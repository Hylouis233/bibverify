"""OpenAlex provider adapter."""

from __future__ import annotations

from typing import Any

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class OpenAlexProvider(MetadataProvider):
    name = "openalex"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        identifiers = extract_identifiers(entry)
        settings = self.config.get("platforms", {}).get(self.name, {})
        params: dict[str, Any] = {"per_page": 5}
        if identifiers.doi:
            params["filter"] = f"doi:{identifiers.doi}"
        elif title.strip():
            params["search"] = self.checker.clean_title(title)
        else:
            return ProviderResult(
                self.name, QueryStatus.INVALID_INPUT, error="Missing title and DOI."
            )
        if settings.get("use_polite_pool", True):
            params["mailto"] = self.checker.user_email
        if settings.get("api_key"):
            params["api_key"] = settings["api_key"]
        data = response_json(
            self.http.get(
                "https://api.openalex.org/works",
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
            )
        )
        candidates = [
            self._candidate(
                entry, self.checker.openalex_to_bibtex(item, entry.get("ID", "reference")), item
            )
            for item in data.get("results", [])
            if isinstance(item, dict)
        ]
        return self._select(candidates)
