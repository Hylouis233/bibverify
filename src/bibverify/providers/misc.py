"""Optional provider adapters with the same structured-result contract."""

from __future__ import annotations

from typing import Any

from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class CoreProvider(MetadataProvider):
    name = "core"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        if not title.strip():
            return ProviderResult(self.name, QueryStatus.INVALID_INPUT, error="Missing title.")
        headers = self._headers()
        api_key = self.config.get("platforms", {}).get(self.name, {}).get("api_key")
        if not api_key:
            return ProviderResult(
                self.name, QueryStatus.AUTH_ERROR, error="CORE requires an API key."
            )
        headers["Authorization"] = f"Bearer {api_key}"
        data = response_json(
            self.http.get(
                "https://api.core.ac.uk/v3/search/works",
                params={"q": f'title:"{self.checker.clean_title(title)}"', "limit": 5},
                headers=headers,
                timeout=self.timeout,
            )
        )
        candidates = [
            self._candidate(
                entry, self.checker.core_to_bibtex(item, entry.get("ID", "reference")), item
            )
            for item in data.get("results", [])
            if isinstance(item, dict)
        ]
        return self._select(candidates)


class BaseSearchProvider(MetadataProvider):
    name = "base"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        if not title.strip():
            return ProviderResult(self.name, QueryStatus.INVALID_INPUT, error="Missing title.")
        data = response_json(
            self.http.get(
                "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi",
                params={
                    "func": "PerformSearch",
                    "query": f'dctitle:"{self.checker.clean_title(title)}"',
                    "format": "json",
                    "hits": 5,
                },
                timeout=self.timeout,
            )
        )
        candidates = [
            self._candidate(
                entry, self.checker.base_to_bibtex(item, entry.get("ID", "reference")), item
            )
            for item in data.get("docs", [])
            if isinstance(item, dict)
        ]
        return self._select(candidates)


class GoogleScholarProvider(MetadataProvider):
    name = "google_scholar"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        try:
            from scholarly import scholarly
        except ImportError:
            return ProviderResult(
                self.name,
                QueryStatus.SKIPPED,
                error="Optional dependency 'scholarly' is not installed.",
            )
        if not title.strip():
            return ProviderResult(self.name, QueryStatus.INVALID_INPUT, error="Missing title.")
        publication = next(scholarly.search_pubs(self.checker.clean_title(title)), None)
        if not publication:
            return ProviderResult(self.name, QueryStatus.NO_MATCH)
        bibtex = scholarly.bibtex(publication)
        normalized = self.checker.google_scholar_to_bibtex(bibtex, entry.get("ID", "reference"))
        return self._select([self._candidate(entry, normalized, bibtex)])
