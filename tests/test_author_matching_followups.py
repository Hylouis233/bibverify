"""Regressions for Codex author-matching follow-ups on PR #48 / #49."""

from __future__ import annotations

from bibverify.matching import (
    assess_match,
    expand_abbreviated_page_range,
    person_lists_equivalent,
)
from bibverify.merge import merge_entries
from bibverify.models import QueryStatus


def test_pubmed_family_first_without_comma_matches_bibtex():
    """PubMed ``Lovelace A`` ≡ BibTeX ``Lovelace, A.`` (PR #48 Codex P1)."""
    result = merge_entries(
        {
            "ID": "lovelace",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Lovelace, A.",
        },
        {
            "ID": "lovelace",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Lovelace A",
        },
        source="pubmed",
        confidence=0.99,
    )
    decision = next(item for item in result.decisions if item.field == "author")
    assert decision.normalized_equal
    assert decision.action == "keep_original"
    assert result.substantive == []
