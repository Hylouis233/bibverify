"""Regressions for Codex author-matching follow-ups on PR #48."""

from __future__ import annotations

from bibverify.merge import merge_entries


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


def test_compact_initials_match_expanded_given_names():
    """``Meyer, MN`` ≡ ``Meyer, Michelle N.`` (PR #48 Codex P2)."""
    result = merge_entries(
        {
            "ID": "meyer",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Meyer, MN",
        },
        {
            "ID": "meyer",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Meyer, Michelle N.",
        },
        source="crossref",
        confidence=0.95,
    )
    decision = next(item for item in result.decisions if item.field == "author")
    assert decision.normalized_equal
    assert decision.action == "keep_original"
    assert result.substantive == []


def test_cjk_single_character_given_names_are_not_initials():
    """``王, 伟`` ≠ ``王, 伟明`` — CJK one-char names are full given names (PR #48 Codex P2)."""
    result = merge_entries(
        {
            "ID": "wang",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "王, 伟",
        },
        {
            "ID": "wang",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "王, 伟明",
        },
        source="crossref",
        confidence=0.95,
    )
    decision = next(item for item in result.decisions if item.field == "author")
    assert not decision.normalized_equal
    assert any(item.field == "author" for item in result.substantive)
