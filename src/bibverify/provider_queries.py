"""Structured provider orchestration plus v0.2-compatible query helpers."""

from __future__ import annotations

from typing import Any

from bibverify.models import Candidate, EntryStatus, ProviderResult, QueryOutcome, QueryStatus


class ProviderQueriesMixin:
    def query_multi_platform_result(
        self, title: str, entry: dict[str, Any] | None = None
    ) -> QueryOutcome:
        """Return an evidence-rich aggregate result across enabled providers."""
        original = dict(entry or {})
        if title and not original.get("title"):
            original["title"] = title
        if (
            not str(original.get("title", "")).strip()
            and not self.extract_identifiers(original).any
        ):
            return QueryOutcome(
                EntryStatus.INVALID_INPUT,
                [],
                complete=False,
                reason="The entry has neither a title nor a supported identifier.",
            )

        provider_results: list[ProviderResult] = []
        matched: list[Candidate] = []
        ambiguous: list[Candidate] = []
        stop_on_first = bool(self.config.get("query_settings", {}).get("stop_on_first_match", True))
        for platform in self._rank_platforms_for_entry(title, original):
            print(f"    {self.lang.get_text('querying_platform', platform=platform.upper())}")
            if platform == "unpaywall":
                result = ProviderResult(
                    platform,
                    QueryStatus.SKIPPED,
                    error="Unpaywall enriches open-access data and is not a verification source.",
                )
            else:
                provider = self.provider_registry.get(platform)
                if provider is None:
                    result = ProviderResult(
                        platform,
                        QueryStatus.SKIPPED,
                        error="No provider adapter is installed.",
                    )
                else:
                    result = provider.lookup(title, original)
            provider_results.append(result)

            if result.status is QueryStatus.IDENTIFIER_CONFLICT:
                print(f"    [{platform.upper()}] identifier conflict")
                return QueryOutcome(
                    EntryStatus.IDENTIFIER_CONFLICT,
                    provider_results,
                    result.best,
                    complete=not any(item.status.is_unavailable for item in provider_results),
                    reason=result.best.assessment.reason if result.best else "Identifier conflict.",
                )
            if result.status is QueryStatus.MATCHED:
                print(f"    {self.lang.get_text('found_match', platform=platform.upper())}")
                matched.extend(result.candidates)
                if stop_on_first:
                    break
            elif result.status is QueryStatus.AMBIGUOUS:
                print(f"    [{platform.upper()}] ambiguous candidate")
                ambiguous.extend(result.candidates)
            elif result.status.is_unavailable:
                print(f"    [{platform.upper()}] {result.status.value}: {result.error or ''}")
            elif result.status is QueryStatus.NO_MATCH:
                print(f"    {self.lang.get_text('not_found', platform=platform.upper())}")

        incomplete = any(result.status.is_unavailable for result in provider_results)
        if matched:
            matched.sort(key=lambda candidate: candidate.confidence, reverse=True)
            return QueryOutcome(
                EntryStatus.VERIFIED,
                provider_results,
                matched[0],
                complete=not incomplete,
                reason="At least one provider returned a high-confidence candidate.",
            )
        if ambiguous:
            ambiguous.sort(key=lambda candidate: candidate.confidence, reverse=True)
            return QueryOutcome(
                EntryStatus.AMBIGUOUS,
                provider_results,
                ambiguous[0],
                complete=not incomplete,
                reason="Only ambiguous candidates were found; no automatic update was made.",
            )

        normal_no_match = any(result.status is QueryStatus.NO_MATCH for result in provider_results)
        if incomplete:
            return QueryOutcome(
                EntryStatus.SOURCE_UNAVAILABLE,
                provider_results,
                complete=False,
                reason=(
                    "Verification is incomplete because one or more metadata providers failed."
                ),
            )
        if normal_no_match:
            return QueryOutcome(
                EntryStatus.NOT_FOUND,
                provider_results,
                complete=True,
                reason="No candidate was found in the providers that completed normally.",
            )
        return QueryOutcome(
            EntryStatus.INVALID_INPUT,
            provider_results,
            complete=False,
            reason="No enabled provider could search this entry.",
        )

    @staticmethod
    def _legacy_candidate(candidate: Candidate | None) -> tuple[Any, ...] | None:
        if candidate is None:
            return None
        if candidate.provider == "arxiv" and isinstance(candidate.payload, tuple):
            return (candidate.provider, *candidate.payload)
        return (candidate.provider, candidate.payload)

    def query_multi_platform(self, title: str, entry: dict[str, Any] | None = None):
        """Compatibility facade returning the historical provider tuple."""
        original = entry or {}
        first_match = None
        stop_on_first = bool(self.config.get("query_settings", {}).get("stop_on_first_match", True))
        for platform in self._rank_platforms_for_entry(title, original):
            if platform == "unpaywall":
                continue
            if platform == "crossref":
                doi = original.get("doi", "")
                result = self.query_crossref_by_doi(doi, title=title) if doi else None
                if not result:
                    result = self.query_crossref(title)
            else:
                method = getattr(self, f"query_{platform}", None)
                result = method(title) if method else None
            if result:
                if stop_on_first:
                    return result
                if first_match is None:
                    first_match = result
        return first_match

    def _legacy_lookup(self, provider: str, title: str, entry: dict[str, Any]):
        adapter = self.provider_registry.get(provider)
        if adapter is None:
            return None
        return self._legacy_candidate(adapter.lookup(title, entry).best)

    def query_crossref_by_doi(self, doi: str, title: str | None = None):
        return self._legacy_lookup(
            "crossref", title or "", {"ID": "reference", "title": title or "", "doi": doi}
        )

    def query_crossref(self, title: str):
        return self._legacy_lookup("crossref", title, {"ID": "reference", "title": title})

    def query_arxiv(self, title: str):
        return self._legacy_lookup("arxiv", title, {"ID": "reference", "title": title})

    def query_openalex(self, title: str):
        return self._legacy_lookup("openalex", title, {"ID": "reference", "title": title})

    def query_semantic_scholar(self, title: str):
        return self._legacy_lookup("semantic_scholar", title, {"ID": "reference", "title": title})

    def query_dblp(self, title: str):
        return self._legacy_lookup("dblp", title, {"ID": "reference", "title": title})

    def query_pubmed(self, title: str):
        return self._legacy_lookup("pubmed", title, {"ID": "reference", "title": title})

    def query_europe_pmc(self, title: str):
        return self._legacy_lookup("europe_pmc", title, {"ID": "reference", "title": title})

    def query_core(self, title: str):
        return self._legacy_lookup("core", title, {"ID": "reference", "title": title})

    def query_base(self, title: str):
        return self._legacy_lookup("base", title, {"ID": "reference", "title": title})

    def query_biorxiv(self, title: str):
        return self._legacy_lookup("biorxiv", title, {"ID": "reference", "title": title})

    def query_google_scholar(self, title: str):
        return self._legacy_lookup("google_scholar", title, {"ID": "reference", "title": title})

    def query_unpaywall(self, title: str, doi: str | None = None):
        return None
