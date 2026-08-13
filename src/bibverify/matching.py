"""Conservative, explainable multi-signal bibliographic matching."""

from __future__ import annotations

import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from bibverify.identifiers import extract_identifiers
from bibverify.models import MatchAssessment, QueryStatus


def normalize_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\\[a-zA-Z]+\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"[{}]", "", text)
    text = unicodedata.normalize("NFKC", text).casefold()
    text = (
        text.replace("\N{GREEK SMALL LETTER BETA}", " beta ")
        .replace("\N{GREEK SMALL LETTER ALPHA}", " alpha ")
        .replace("\N{GREEK SMALL LETTER GAMMA}", " gamma ")
    )
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(left: Any, right: Any) -> float:
    first = normalize_text(left)
    second = normalize_text(right)
    if not first or not second:
        return 0.0
    if first == second:
        return 1.0
    sequence = SequenceMatcher(None, first, second).ratio()
    first_tokens = set(first.split())
    second_tokens = set(second.split())
    union = first_tokens | second_tokens
    jaccard = len(first_tokens & second_tokens) / len(union) if union else 0.0
    shorter, longer = sorted((first, second), key=len)
    containment = 0.0
    if shorter in longer and len(shorter.split()) >= 4 and len(shorter) / len(longer) >= 0.65:
        containment = len(shorter) / len(longer)
    return max(sequence, jaccard, containment)


def _authors(value: Any) -> set[str]:
    text = html.unescape(str(value or ""))
    if not text.strip():
        return set()
    names = re.split(r"\s+and\s+|\s*;\s*", text, flags=re.IGNORECASE)
    normalized = set()
    for name in names:
        # BibTeX commonly represents authors as ``Family, Given`` while many
        # APIs return ``Given Family``. Compare family-name tokens in either
        # representation without changing the serialized author field.
        family = name.split(",", 1)[0] if "," in name else name.split()[-1]
        family = normalize_text(family)
        if family:
            normalized.add(family)
    return normalized


def _overlap(left: set[str], right: set[str]) -> float | None:
    if not left or not right:
        return None
    return len(left & right) / len(left | right)


def _year(value: Any) -> int | None:
    match = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return int(match.group(0)) if match else None


def assess_match(
    original: dict[str, Any],
    candidate: dict[str, Any],
    *,
    matched_threshold: float = 0.86,
    ambiguous_threshold: float = 0.68,
) -> MatchAssessment:
    """Score a candidate and explicitly expose identifier conflicts."""
    original_ids = extract_identifiers(original)
    candidate_ids = extract_identifiers(candidate)
    shared_ids: list[str] = []
    conflicting_ids: list[str] = []
    for name in ("doi", "pmid", "pmcid", "arxiv"):
        left = getattr(original_ids, name)
        right = getattr(candidate_ids, name)
        if left and right:
            (shared_ids if left == right else conflicting_ids).append(name)

    title = title_similarity(original.get("title"), candidate.get("title"))
    if conflicting_ids:
        return MatchAssessment(
            score=0.0,
            status=QueryStatus.IDENTIFIER_CONFLICT,
            signals={
                "title": round(title, 4),
                "identifier_exact": False,
                "identifier_conflicts": ",".join(conflicting_ids),
            },
            reason=f"Conflicting identifiers: {', '.join(conflicting_ids)}",
        )
    original_has_title = bool(normalize_text(original.get("title")))
    candidate_has_title = bool(normalize_text(candidate.get("title")))
    if shared_ids and original_has_title and candidate_has_title and title < 0.45:
        return MatchAssessment(
            score=0.0,
            status=QueryStatus.IDENTIFIER_CONFLICT,
            signals={
                "title": round(title, 4),
                "identifier_exact": True,
                "shared_identifiers": ",".join(shared_ids),
            },
            reason="The identifier resolves, but the returned title is materially different.",
        )

    weighted: list[tuple[float, float]] = []
    if original.get("title") and candidate.get("title"):
        weighted.append((title, 0.55))
    author_score = _overlap(_authors(original.get("author")), _authors(candidate.get("author")))
    if author_score is not None:
        weighted.append((author_score, 0.20))
    original_year = _year(original.get("year"))
    candidate_year = _year(candidate.get("year"))
    year_score: float | None = None
    if original_year is not None and candidate_year is not None:
        delta = abs(original_year - candidate_year)
        year_score = 1.0 if delta == 0 else 0.65 if delta == 1 else 0.0
        weighted.append((year_score, 0.10))
    venue_left = original.get("journal") or original.get("booktitle")
    venue_right = candidate.get("journal") or candidate.get("booktitle")
    venue_score: float | None = None
    if venue_left and venue_right:
        venue_score = title_similarity(venue_left, venue_right)
        weighted.append((venue_score, 0.10))
    page_score: float | None = None
    if original.get("pages") and candidate.get("pages"):
        page_score = float(normalize_text(original["pages"]) == normalize_text(candidate["pages"]))
        weighted.append((page_score, 0.05))

    if shared_ids:
        score = max(
            0.95,
            sum(value * weight for value, weight in weighted)
            / sum(weight for _, weight in weighted)
            if weighted
            else 1.0,
        )
    elif weighted:
        score = sum(value * weight for value, weight in weighted) / sum(
            weight for _, weight in weighted
        )
    else:
        score = 0.0

    signals: dict[str, float | bool | str | None] = {
        "title": round(title, 4),
        "authors": round(author_score, 4) if author_score is not None else None,
        "year": year_score,
        "venue": round(venue_score, 4) if venue_score is not None else None,
        "pages": page_score,
        "identifier_exact": bool(shared_ids),
        "shared_identifiers": ",".join(shared_ids) if shared_ids else None,
    }
    exact_identifier_without_input_title = bool(
        shared_ids and not original_has_title and candidate_has_title
    )
    supporting_signal = any(
        signal is not None for signal in (author_score, year_score, venue_score, page_score)
    )
    title_only = not shared_ids and not supporting_signal
    if title_only and title >= ambiguous_threshold:
        status = QueryStatus.AMBIGUOUS
        reason = "Title agreement alone is insufficient for an automatic match."
    elif score >= matched_threshold and (title >= 0.60 or exact_identifier_without_input_title):
        status = QueryStatus.MATCHED
        reason = "High-confidence agreement across available bibliographic signals."
    elif score >= ambiguous_threshold or (shared_ids and title >= 0.45):
        status = QueryStatus.AMBIGUOUS
        reason = "The candidate is plausible but does not meet the automatic-match threshold."
    else:
        status = QueryStatus.NO_MATCH
        reason = "Available signals do not support this candidate."
    return MatchAssessment(score=score, status=status, signals=signals, reason=reason)
