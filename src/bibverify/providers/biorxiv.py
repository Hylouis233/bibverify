"""bioRxiv API adapter.

The official details route supports DOI/date lookup, not arbitrary title
search. Title-only entries are therefore skipped explicitly rather than
misreported as absent.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class BiorxivProvider(MetadataProvider):
    name = "biorxiv"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(entry))

    def _lookup(self, entry: dict[str, Any]) -> ProviderResult:
        doi = extract_identifiers(entry).doi
        if not doi.startswith("10.1101/"):
            return ProviderResult(
                self.name,
                QueryStatus.SKIPPED,
                error="The official bioRxiv API supports exact DOI/date lookup, not title search.",
            )
        data = response_json(
            self.http.get(
                f"https://api.biorxiv.org/details/biorxiv/{quote(doi, safe='')}",
                headers=self._headers(),
                timeout=self.timeout,
            )
        )
        candidates = [
            self._candidate(
                entry, self.checker.biorxiv_to_bibtex(item, entry.get("ID", "reference")), item
            )
            for item in data.get("collection", [])
            if isinstance(item, dict)
        ]
        return self._select(candidates)
