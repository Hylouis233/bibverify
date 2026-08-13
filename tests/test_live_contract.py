"""Small non-blocking live API checks run by the scheduled workflow only."""

from __future__ import annotations

import os

import pytest

from bibverify.checker import BibTeXChecker
from bibverify.models import QueryStatus

pytestmark = pytest.mark.live


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

    assert result.status in {QueryStatus.MATCHED, QueryStatus.AMBIGUOUS}
