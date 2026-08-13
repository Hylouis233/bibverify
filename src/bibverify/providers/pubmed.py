"""NCBI PubMed provider using identifier-first ESummary requests."""

from __future__ import annotations

from typing import Any

from bibverify.identifiers import extract_identifiers
from bibverify.models import ProviderResult, QueryStatus
from bibverify.providers.base import MetadataProvider, response_json


class PubmedProvider(MetadataProvider):
    name = "pubmed"

    def lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        return self._run(lambda: self._lookup(title, entry))

    def _params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        api_key = self.config.get("platforms", {}).get(self.name, {}).get("api_key")
        if api_key:
            params["api_key"] = api_key
        if self.checker.user_email:
            params["email"] = self.checker.user_email
        params["tool"] = self.checker.app_name
        return params

    def _lookup(self, title: str, entry: dict[str, Any]) -> ProviderResult:
        identifiers = extract_identifiers(entry)
        pmids: list[str] = []
        params = self._params()
        if identifiers.pmid:
            pmids = [identifiers.pmid]
        else:
            if identifiers.pmcid:
                term = f"{identifiers.pmcid}[PMCID]"
            elif identifiers.doi:
                term = f'"{identifiers.doi}"[DOI]'
            elif title.strip():
                term = f'"{self.checker.clean_title(title)}"[Title]'
            else:
                return ProviderResult(
                    self.name, QueryStatus.INVALID_INPUT, error="Missing searchable metadata."
                )
            search_params = {"db": "pubmed", "term": term, "retmode": "json", "retmax": 5}
            search_params.update(params)
            data = response_json(
                self.http.get(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                    params=search_params,
                    timeout=self.timeout,
                )
            )
            pmids = list(data.get("esearchresult", {}).get("idlist", []))
        if not pmids:
            return ProviderResult(self.name, QueryStatus.NO_MATCH)

        fetch_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
        fetch_params.update(params)
        data = response_json(
            self.http.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params=fetch_params,
                timeout=self.timeout,
            )
        )
        result = data.get("result", {})
        candidates = [
            self._candidate(
                entry,
                self.checker.pubmed_to_bibtex(result[pmid], entry.get("ID", "reference")),
                result[pmid],
            )
            for pmid in pmids
            if isinstance(result.get(pmid), dict)
        ]
        return self._select(candidates)
