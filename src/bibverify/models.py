"""Typed result models shared by providers, matching, reporting, and transports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class QueryStatus(StrEnum):
    """Outcome of one metadata-provider operation."""

    MATCHED = "matched"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    PROVIDER_ERROR = "provider_error"
    IDENTIFIER_CONFLICT = "identifier_conflict"
    INVALID_INPUT = "invalid_input"
    SKIPPED = "skipped"

    @property
    def is_unavailable(self) -> bool:
        return self in {
            self.RATE_LIMITED,
            self.AUTH_ERROR,
            self.NETWORK_ERROR,
            self.PARSE_ERROR,
            self.PROVIDER_ERROR,
        }


class EntryStatus(StrEnum):
    """User-facing verification state for one bibliography entry."""

    VERIFIED = "verified"
    METADATA_MISMATCH = "metadata_mismatch"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    INVALID_INPUT = "invalid_input"
    IDENTIFIER_CONFLICT = "identifier_conflict"


@dataclass(slots=True)
class MatchAssessment:
    """Multi-signal comparison between an input entry and one candidate."""

    score: float
    status: QueryStatus
    signals: dict[str, float | bool | str | None] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "status": self.status.value,
            "signals": dict(self.signals),
            "reason": self.reason,
        }


@dataclass(slots=True)
class Candidate:
    """Normalized bibliographic candidate with an optional provider-native payload."""

    provider: str
    entry: dict[str, Any]
    assessment: MatchAssessment
    payload: Any = field(default=None, repr=False)

    @property
    def confidence(self) -> float:
        return self.assessment.score

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "entry": dict(self.entry),
            "confidence": round(self.confidence, 4),
            "match": self.assessment.to_dict(),
        }


@dataclass(slots=True)
class ProviderResult:
    """Structured result returned by every provider adapter."""

    provider: str
    status: QueryStatus
    candidates: list[Candidate] = field(default_factory=list)
    error: str | None = None
    elapsed_ms: int | None = None
    http_status: int | None = None

    @property
    def available(self) -> bool:
        return not self.status.is_unavailable

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "provider": self.provider,
            "status": self.status.value,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }
        if self.error:
            result["error"] = self.error
        if self.elapsed_ms is not None:
            result["elapsed_ms"] = self.elapsed_ms
        if self.http_status is not None:
            result["http_status"] = self.http_status
        return result


@dataclass(slots=True)
class QueryOutcome:
    """Aggregate outcome across every provider consulted for one entry."""

    status: EntryStatus
    provider_results: list[ProviderResult]
    best_candidate: Candidate | None = None
    complete: bool = True
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "complete": self.complete,
            "confidence": (
                round(self.best_candidate.confidence, 4) if self.best_candidate else None
            ),
            "reason": self.reason,
            "best_candidate": self.best_candidate.to_dict() if self.best_candidate else None,
            "provider_status": [result.to_dict() for result in self.provider_results],
        }


@dataclass(slots=True)
class FieldChange:
    """Field-level merge decision with provenance."""

    field: str
    original: str
    suggested: str
    normalized_equal: bool
    source: str
    confidence: float
    action: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "original": self.original,
            "suggested": self.suggested,
            "normalized_equal": self.normalized_equal,
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "action": self.action,
            "reason": self.reason,
        }
