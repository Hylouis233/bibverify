"""Non-destructive, confidence-aware BibTeX field merging."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bibverify.identifiers import (
    canonicalize_arxiv,
    canonicalize_doi,
    canonicalize_pmcid,
    canonicalize_pmid,
)
from bibverify.matching import normalize_text
from bibverify.models import FieldChange

IDENTIFIER_FIELDS = {"doi", "pmid", "pmcid", "eprint"}
CONSERVATIVE_FIELDS = {
    "title",
    "author",
    "editor",
    "journal",
    "booktitle",
    "year",
    "volume",
    "number",
    "pages",
    "publisher",
    "ENTRYTYPE",
}


def normalize_field(field: str, value: Any) -> str:
    text = str(value or "").strip()
    lowered = field.lower()
    if lowered == "doi":
        return canonicalize_doi(text)
    if lowered == "pmid":
        return canonicalize_pmid(text)
    if lowered == "pmcid":
        return canonicalize_pmcid(text)
    if lowered == "eprint":
        return canonicalize_arxiv(text) or normalize_text(text)
    if lowered == "pages":
        return re.sub(r"[-\u2013\u2014]+", "-", normalize_text(text))
    if lowered in {"year", "volume", "number"}:
        return re.sub(r"\D", "", text)
    return normalize_text(text)


@dataclass(slots=True)
class MergeResult:
    entry: dict[str, Any]
    decisions: list[FieldChange]

    @property
    def applied(self) -> list[FieldChange]:
        return [item for item in self.decisions if item.action in {"add", "update"}]

    @property
    def differences(self) -> dict[str, dict[str, Any]]:
        return {
            item.field: {
                "original": item.original,
                "updated": item.suggested,
                "source": item.source,
                "confidence": round(item.confidence, 4),
                "action": item.action,
                "reason": item.reason,
            }
            for item in self.applied
        }


def merge_entries(
    original: dict[str, Any],
    candidate: dict[str, Any],
    *,
    source: str,
    confidence: float,
    auto_update_threshold: float = 0.92,
) -> MergeResult:
    """Merge trusted candidate fields without removing any original field."""
    merged = dict(original)
    decisions: list[FieldChange] = []
    for field, suggested_value in candidate.items():
        if field == "ID" or suggested_value is None or not str(suggested_value).strip():
            continue
        original_value = original.get(field, "")
        original_text = str(original_value or "").strip()
        suggested_text = str(suggested_value).strip()
        normalized_equal = normalize_field(field, original_text) == normalize_field(
            field, suggested_text
        )
        if normalized_equal and original_text:
            action = "keep_original"
            reason = "Values are equivalent after field-specific normalization."
        elif not original_text:
            action = "add" if confidence >= auto_update_threshold else "suggest"
            reason = (
                "The provider supplied a missing field at sufficient confidence."
                if action == "add"
                else "The missing field is reported for review because confidence is insufficient."
            )
        elif field.lower() in IDENTIFIER_FIELDS:
            action = "manual_review"
            reason = "A differing persistent identifier is never overwritten automatically."
        elif field in CONSERVATIVE_FIELDS and confidence >= auto_update_threshold:
            action = "update"
            reason = "A high-confidence candidate supports replacing this bibliographic field."
        else:
            action = "suggest"
            reason = "The difference is retained as a suggestion for manual review."

        if action in {"add", "update"}:
            merged[field] = suggested_value
        decisions.append(
            FieldChange(
                field=field,
                original=original_text,
                suggested=suggested_text,
                normalized_equal=normalized_equal,
                source=source,
                confidence=confidence,
                action=action,
                reason=reason,
            )
        )
    return MergeResult(entry=merged, decisions=decisions)
