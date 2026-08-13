"""arXiv Atom API adapter with exact id_list support."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider

ATOM = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivProvider(MetadataProvider):
    name = "arxiv"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        identifiers = extract_identifiers(entry)
        if identifiers.arxiv:
            params: dict[str, Any] = {"id_list": identifiers.arxiv, "max_results": 1}
        elif title.strip():
            clean = self.checker.clean_title(title).replace('"', "")
            params = {"search_query": f'ti:"{clean}"', "max_results": 5}
        else:
            return ProviderResult(
                self.name, QueryStatus.INVALID_INPUT, error="Missing searchable metadata."
            )
        response = self.http.get(
            "https://export.arxiv.org/api/query", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
        candidates = []
        for item in root.findall("atom:entry", ATOM):
            normalized = self.checker.arxiv_to_bibtex(item, ATOM, entry.get("ID", "reference"))
            candidates.append(self._candidate(entry, normalized, (item, ATOM)))
        return self._select(candidates)
