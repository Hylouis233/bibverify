"""Europe PMC provider with DOI, PMID, PMCID, then title lookup."""

from __future__ import annotations

from typing import Any

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class EuropePmcProvider(MetadataProvider):
    name = "europe_pmc"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        identifiers = extract_identifiers(entry)
        if identifiers.pmid:
            query = f"EXT_ID:{identifiers.pmid} AND SRC:MED"
        elif identifiers.pmcid:
            query = f"PMCID:{identifiers.pmcid}"
        elif identifiers.doi:
            query = f'DOI:"{identifiers.doi}"'
        elif title.strip():
            escaped = self.checker.clean_title(title).replace('"', "")
            query = f'TITLE:"{escaped}"'
        else:
            return ProviderResult(
                self.name, QueryStatus.INVALID_INPUT, error="Missing searchable metadata."
            )
        data = response_json(
            self.http.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": query, "format": "json", "pageSize": 5},
                timeout=self.timeout,
            )
        )
        candidates = [
            self._candidate(
                entry, self.checker.europe_pmc_to_bibtex(item, entry.get("ID", "reference")), item
            )
            for item in data.get("resultList", {}).get("result", [])
            if isinstance(item, dict)
        ]
        return self._select(candidates)
