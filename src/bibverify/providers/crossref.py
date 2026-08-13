"""Crossref provider adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class CrossrefProvider(MetadataProvider):
    name = "crossref"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _params(self) -> dict[str, str]:
        settings = self.config.get("platforms", {}).get(self.name, {})
        return {"mailto": self.checker.user_email} if settings.get("use_polite_pool", True) else {}

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        identifiers = extract_identifiers(entry)
        if identifiers.doi:
            response = self.http.get(
                f"https://api.crossref.org/works/{quote(identifiers.doi, safe='')}",
                params=self._params(),
                headers=self._headers(),
                timeout=self.timeout,
            )
            if response.status_code != 404:
                data = response_json(response).get("message", {})
                if not isinstance(data, dict):
                    raise ValueError("Crossref message is not an object.")
                candidate = self._candidate(
                    entry, self.checker.crossref_to_bibtex(data, entry.get("ID", "reference")), data
                )
                return self._select([candidate])
            if not title.strip():
                return ProviderResult(self.name, QueryStatus.NO_MATCH)

        if not title.strip():
            return ProviderResult(
                self.name, QueryStatus.INVALID_INPUT, error="Missing title and DOI."
            )
        params: dict[str, Any] = {"query.title": self.checker.clean_title(title), "rows": 5}
        params.update(self._params())
        data = response_json(
            self.http.get(
                "https://api.crossref.org/works",
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
        )
        items = data.get("message", {}).get("items", [])
        candidates = [
            self._candidate(
                entry, self.checker.crossref_to_bibtex(item, entry.get("ID", "reference")), item
            )
            for item in items
            if isinstance(item, dict)
        ]
        return self._select(candidates)
