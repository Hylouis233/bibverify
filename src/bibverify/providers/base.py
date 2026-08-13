"""Shared provider protocol, error classification, and candidate selection."""

from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import requests

from bibverify.matching import assess_match
from bibverify.models import Candidate, ProviderResult, QueryStatus


class MetadataProvider(ABC):
    name = "provider"

    def __init__(self, checker: Any) -> None:
        self.checker = checker
        self.http = checker.http
        self.config = checker.config

    @abstractmethod
    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        """Look up an entry using exact identifiers first, then title search."""

    def _run(self, operation: Callable[[], ProviderResult]) -> ProviderResult:
        started = time.perf_counter()
        try:
            result = operation()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 404:
                query_status = QueryStatus.NO_MATCH
            elif status == 429:
                query_status = QueryStatus.RATE_LIMITED
            elif status in {401, 403}:
                query_status = QueryStatus.AUTH_ERROR
            else:
                query_status = QueryStatus.PROVIDER_ERROR
            result = ProviderResult(
                self.name,
                query_status,
                error=self._safe_error(exc),
                http_status=status,
            )
        except (json.JSONDecodeError, requests.exceptions.JSONDecodeError, ET.ParseError) as exc:
            result = ProviderResult(self.name, QueryStatus.PARSE_ERROR, error=self._safe_error(exc))
        except requests.exceptions.Timeout as exc:
            result = ProviderResult(
                self.name, QueryStatus.NETWORK_ERROR, error=f"Timeout: {self._safe_error(exc)}"
            )
        except requests.exceptions.RequestException as exc:
            result = ProviderResult(
                self.name, QueryStatus.NETWORK_ERROR, error=self._safe_error(exc)
            )
        except (KeyError, TypeError, ValueError) as exc:
            result = ProviderResult(self.name, QueryStatus.PARSE_ERROR, error=self._safe_error(exc))
        except Exception as exc:  # Provider boundaries must isolate third-party failures.
            result = ProviderResult(
                self.name, QueryStatus.PROVIDER_ERROR, error=self._safe_error(exc)
            )
        result.elapsed_ms = round((time.perf_counter() - started) * 1000)
        return result

    @staticmethod
    def _safe_error(exc: BaseException) -> str:
        return str(exc).replace("\r", " ").replace("\n", " ")[:300] or type(exc).__name__

    def _candidate(
        self,
        original: dict[str, Any],
        normalized_entry: dict[str, Any],
        payload: Any,
    ) -> Candidate:
        settings = self.config.get("query_settings", {})
        assessment = assess_match(
            original,
            normalized_entry,
            matched_threshold=float(settings.get("match_threshold", 0.86)),
            ambiguous_threshold=float(settings.get("ambiguous_threshold", 0.68)),
        )
        return Candidate(self.name, normalized_entry, assessment, payload=payload)

    def _select(self, candidates: list[Candidate]) -> ProviderResult:
        conflicts = [
            candidate
            for candidate in candidates
            if candidate.assessment.status is QueryStatus.IDENTIFIER_CONFLICT
        ]
        if conflicts:
            return ProviderResult(self.name, QueryStatus.IDENTIFIER_CONFLICT, conflicts)

        viable = [
            candidate
            for candidate in candidates
            if candidate.assessment.status in {QueryStatus.MATCHED, QueryStatus.AMBIGUOUS}
        ]
        viable.sort(key=lambda candidate: candidate.confidence, reverse=True)
        if not viable:
            return ProviderResult(self.name, QueryStatus.NO_MATCH)

        best = viable[0]
        margin = float(self.config.get("query_settings", {}).get("ambiguity_margin", 0.04))
        if len(viable) > 1 and best.confidence - viable[1].confidence <= margin:
            return ProviderResult(self.name, QueryStatus.AMBIGUOUS, viable)
        return ProviderResult(self.name, best.assessment.status, viable)

    def _headers(self, **extra: str) -> dict[str, str]:
        headers = {
            "User-Agent": f"{self.checker.app_name}/0.3 (mailto:{self.checker.user_email})",
            "Accept": "application/json",
        }
        headers.update(extra)
        return headers

    @property
    def timeout(self) -> tuple[float, float]:
        query = self.config.get("query_settings", {})
        return (
            float(query.get("connect_timeout", 3.05)),
            float(query.get("read_timeout", query.get("timeout", 20.0))),
        )


def response_json(response: requests.Response) -> dict[str, Any]:
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Provider response root is not an object.")
    return data
