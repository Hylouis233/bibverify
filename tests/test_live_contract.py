"""Small non-blocking live API checks run by the scheduled workflow only."""

from __future__ import annotations

import os

import pytest

from bibverify.checker import BibTeXChecker
from bibverify.models import ProviderResult, QueryStatus


def _assert_public_doi_result(provider, result):
    if provider == "semantic_scholar" and result.status is QueryStatus.RATE_LIMITED:
        pytest.skip(f"{provider} live contract inconclusive (HTTP {result.http_status or 429})")

    assert result.status in {QueryStatus.MATCHED, QueryStatus.AMBIGUOUS}


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("BIBVERIFY_LIVE_TESTS"), reason="scheduled live test only")
@pytest.mark.parametrize("provider", ["crossref", "openalex", "semantic_scholar"])
def test_public_doi_contract(provider, tmp_path):
    checker = BibTeXChecker(
        tmp_path / "missing.json",
        overrides={
            "query_settings": {"cache_enabled": False, "delay_between_requests": 0},
        },
    )
    entry = {
        "ID": "nature2013",
        "ENTRYTYPE": "article",
        "title": "Nanometre-scale thermometry in a living cell",
        "doi": "10.1038/nature12373",
        "year": "2013",
    }

    result = checker.provider_registry[provider].lookup(entry["title"], entry)

    _assert_public_doi_result(provider, result)


def test_semantic_scholar_rate_limit_is_inconclusive():
    result = ProviderResult("semantic_scholar", QueryStatus.RATE_LIMITED, http_status=429)

    with pytest.raises(pytest.skip.Exception, match=r"semantic_scholar.*429"):
        _assert_public_doi_result("semantic_scholar", result)


def test_other_provider_rate_limit_remains_a_contract_failure():
    result = ProviderResult("openalex", QueryStatus.RATE_LIMITED, http_status=429)

    with pytest.raises(AssertionError):
        _assert_public_doi_result("openalex", result)


@pytest.mark.parametrize(
    "status",
    [
        QueryStatus.AUTH_ERROR,
        QueryStatus.NETWORK_ERROR,
        QueryStatus.PARSE_ERROR,
        QueryStatus.PROVIDER_ERROR,
    ],
)
def test_semantic_scholar_non_rate_errors_remain_contract_failures(status):
    result = ProviderResult("semantic_scholar", status)

    with pytest.raises(AssertionError):
        _assert_public_doi_result("semantic_scholar", result)


@pytest.mark.parametrize("status", [QueryStatus.MATCHED, QueryStatus.AMBIGUOUS])
def test_public_doi_contract_accepts_match_results(status):
    _assert_public_doi_result("semantic_scholar", ProviderResult("semantic_scholar", status))
