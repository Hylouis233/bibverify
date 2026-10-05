"""Conservative, explainable multi-signal bibliographic matching."""

from __future__ import annotations

import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

from bibverify.identifiers import extract_identifiers
from bibverify.models import MatchAssessment, QueryStatus

_GENERATIONAL_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq"})


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


def expand_abbreviated_page_range(text: str) -> str:
    """Expand BibTeX-style abbreviated end pages (``683--97`` → ``683-697``)."""
    normalized = re.sub(r"[-\u2013\u2014]+", "-", text.strip())
    match = re.fullmatch(r"(\d+)-(\d+)", normalized)
    if not match:
        return normalized
    start, end = match.group(1), match.group(2)
    if 0 < len(end) < len(start):
        expanded = start[: -len(end)] + end
        if int(expanded) >= int(start):
            end = expanded
    return f"{start}-{end}"


def normalize_pages(value: Any) -> str:
    # Expand abbreviated end pages before normalize_text strips hyphens.
    dashed = re.sub(r"[-\u2013\u2014]+", "-", str(value or "").strip())
    return normalize_text(expand_abbreviated_page_range(dashed))


def _is_latin_initial(token: str) -> bool:
    """True for a single Latin letter used as an initial (not a CJK given name)."""
    return len(token) == 1 and token.isascii() and token.isalpha()


def _raw_token_looks_like_latin_initials(token: str) -> bool:
    """Evidence that a *source* token is Latin initials, not a short surname/given name.

    Compact blocks need uppercase or dotted form (``MN``, ``M.N.``). A mixed-case
    short surname such as ``Li`` / ``Kim`` must not trigger PubMed family-first parsing.
    """
    stripped = token.replace(".", "")
    if not stripped.isascii() or not stripped.isalpha():
        return False
    folded = stripped.casefold()
    if folded in _GENERATIONAL_SUFFIXES:
        return False
    if len(stripped) == 1:
        return True
    if 2 <= len(stripped) <= 4:
        return stripped.isupper() or ("." in token)
    return False


def _expanded_matches_latin_initial(name: str, initial: str) -> bool:
    """Latin initial may expand onto an accented given name (``J`` ≡ ``josé``)."""
    return (
        _is_latin_initial(initial) and len(name) > 1 and name.isalpha() and name.startswith(initial)
    )


def _collapse_initials(tokens: list[str]) -> list[str]:
    """Join adjacent single-letter tokens so ``P M`` matches ``PM``."""
    collapsed: list[str] = []
    buffer: list[str] = []
    for token in tokens:
        if _is_latin_initial(token):
            buffer.append(token)
            continue
        if buffer:
            collapsed.append("".join(buffer))
            buffer = []
        collapsed.append(token)
    if buffer:
        collapsed.append("".join(buffer))
    return collapsed


def _split_given_tokens_from_raw(raw_given: str) -> list[str]:
    """Normalize given-name tokens; split uppercase/dotted compact initials into letters."""
    raw_given = raw_given.strip()
    if not raw_given:
        return []
    # Single compact initials token written as ``MN`` / ``M.N.`` (not ``Amy``).
    if _raw_token_looks_like_latin_initials(raw_given) and " " not in raw_given:
        stripped = raw_given.replace(".", "")
        if len(stripped) >= 2:
            return list(stripped.casefold())
    return normalize_text(raw_given).split()


def normalize_person_list(value: Any) -> str:
    """Normalize author/editor lists for equivalence checks."""
    text = str(value or "").strip()
    if not text:
        return ""
    names = re.split(r"\s+and\s+|\s*;\s*", text, flags=re.IGNORECASE)
    normalized_names: list[str] = []
    for name in names:
        tokens = _collapse_initials(normalize_text(name).split())
        if tokens:
            normalized_names.append(" ".join(tokens))
    return " and ".join(normalized_names)


def _parse_person_name(name: str) -> tuple[str, list[str]]:
    """Split a person into ``(family, given_tokens)`` without collapsing initials."""
    raw = str(name or "").strip()
    if not raw:
        return "", []
    if "," in raw:
        family, given = raw.split(",", 1)
        return normalize_text(family), _split_given_tokens_from_raw(given)
    raw_tokens = re.split(r"\s+", raw)
    tokens = normalize_text(raw).split()
    if not tokens:
        return "", []
    # PubMed-style ``Family I`` / ``Family MN`` (no comma): trailing Latin initials
    # only when the *source* token looks like initials (not short surnames like ``Li``).
    if len(raw_tokens) >= 2 and _raw_token_looks_like_latin_initials(raw_tokens[-1]):
        trailing = raw_tokens[-1]
        stripped = trailing.replace(".", "")
        given_tokens = list(stripped.casefold()) if len(stripped) >= 2 else [stripped.casefold()]
        return " ".join(tokens[:-1]), given_tokens
    # Western ``Given Family``
    return tokens[-1], tokens[:-1]


def _given_tokens_equivalent(left: list[str], right: list[str]) -> bool:
    """Allow Latin initials to match expanded given names; keep full-name disagreements."""
    if _collapse_initials(left) == _collapse_initials(right):
        return True
    return _align_given_tokens(left, right)


def _align_given_tokens(left: list[str], right: list[str]) -> bool:
    """Iterative two-pointer alignment for Latin initials (avoids RecursionError)."""
    stack: list[tuple[int, int]] = [(0, 0)]
    seen: set[tuple[int, int]] = set()
    while stack:
        left_index, right_index = stack.pop()
        if (left_index, right_index) in seen:
            continue
        seen.add((left_index, right_index))
        if left_index == len(left) and right_index == len(right):
            return True
        if left_index == len(left) or right_index == len(right):
            continue
        first = left[left_index]
        second = right[right_index]
        if first == second:
            stack.append((left_index + 1, right_index + 1))
        if _expanded_matches_latin_initial(second, first):
            stack.append((left_index + 1, right_index + 1))
        if _expanded_matches_latin_initial(first, second):
            stack.append((left_index + 1, right_index + 1))
    return False


def person_lists_equivalent(left: Any, right: Any) -> bool:
    """True when two author/editor lists name the same people under light variants.

    Accepts initials vs expanded given names (``M. N.`` / ``MN`` ≡ ``Michelle N.``,
    ``W`` ≡ ``William``), PubMed-style ``Family I`` forms, and punctuation/case
    variants that keep family/given ordering, but still treats distinct expanded
    given names (including single-character CJK names) as different.
    """
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    # Fast path only when comma structure matches, so ``Benjamin, Franklin`` is
    # not treated as equivalent to ``Benjamin Franklin``.
    if ("," in left_text) == ("," in right_text):
        if normalize_person_list(left_text) == normalize_person_list(right_text):
            return True
    left_names = [
        part
        for part in re.split(r"\s+and\s+|\s*;\s*", left_text, flags=re.IGNORECASE)
        if part.strip()
    ]
    right_names = [
        part
        for part in re.split(r"\s+and\s+|\s*;\s*", right_text, flags=re.IGNORECASE)
        if part.strip()
    ]
    if len(left_names) != len(right_names):
        return False
    if not left_names and not right_names:
        return True
    for left_name, right_name in zip(left_names, right_names, strict=True):
        left_family, left_given = _parse_person_name(left_name)
        right_family, right_given = _parse_person_name(right_name)
        if left_family != right_family:
            return False
        if not _given_tokens_equivalent(left_given, right_given):
            return False
    return True


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
    normalized: set[str] = set()
    for name in names:
        family, _given = _parse_person_name(name)
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
        page_score = float(
            normalize_pages(original["pages"]) == normalize_pages(candidate["pages"])
        )
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
