"""Semantic Scholar Graph API adapter."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json

FIELDS = "title,authors,year,venue,externalIds,publicationTypes,journal,publicationDate,url"


class SemanticScholarProvider(MetadataProvider):
    name = "semantic_scholar"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        identifiers = extract_identifiers(entry)
        headers = self._headers()
        api_key = self.config.get("platforms", {}).get(self.name, {}).get("api_key")
        if api_key:
            headers["x-api-key"] = api_key

        identifier = ""
        if identifiers.doi:
            identifier = f"DOI:{identifiers.doi}"
        elif identifiers.arxiv:
            identifier = f"ARXIV:{identifiers.arxiv}"
        elif identifiers.pmid:
            identifier = f"PMID:{identifiers.pmid}"
        if identifier:
            response = self.http.get(
                f"https://api.semanticscholar.org/graph/v1/paper/{quote(identifier, safe=':')}",
                params={"fields": FIELDS},
                headers=headers,
                timeout=self.timeout,
            )
            if response.status_code != 404:
                item = response_json(response)
                candidate = self._candidate(
                    entry,
                    self.checker.semantic_scholar_to_bibtex(item, entry.get("ID", "reference")),
                    item,
                )
                return self._select([candidate])
            if not title.strip():
                return ProviderResult(self.name, QueryStatus.NO_MATCH)

        if not title.strip():
            return ProviderResult(
                self.name, QueryStatus.INVALID_INPUT, error="Missing searchable metadata."
            )
        data = response_json(
            self.http.get(
                "https://api.semanticscholar.org/graph/v1/paper/search/match",
                params={"query": self.checker.clean_title(title), "fields": FIELDS},
                headers=headers,
                timeout=self.timeout,
            )
        )
        raw_items = data.get("data", data)
        items = raw_items if isinstance(raw_items, list) else [raw_items]
        candidates = [
            self._candidate(
                entry,
                self.checker.semantic_scholar_to_bibtex(item, entry.get("ID", "reference")),
                item,
            )
            for item in items
            if isinstance(item, dict) and item.get("title")
        ]
        return self._select(candidates)
