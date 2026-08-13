"""DBLP publication search adapter."""

from __future__ import annotations

from typing import Any

from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class DblpProvider(MetadataProvider):
    name = "dblp"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        if not title.strip():
            return ProviderResult(self.name, QueryStatus.INVALID_INPUT, error="Missing title.")
        data = response_json(
            self.http.get(
                "https://dblp.org/search/publ/api",
                params={"q": self.checker.clean_title(title), "format": "json", "h": 5},
                timeout=self.timeout,
            )
        )
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        candidates = []
        for hit in hits:
            info = hit.get("info", {}) if isinstance(hit, dict) else {}
            if isinstance(info, dict):
                normalized = self.checker.dblp_to_bibtex(info, entry.get("ID", "reference"))
                candidates.append(self._candidate(entry, normalized, info))
        return self._select(candidates)
