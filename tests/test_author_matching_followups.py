"""Regressions for Codex author-matching follow-ups on PR #48 / #49."""

from __future__ import annotations

from bibverify.matching import assess_match, person_lists_equivalent
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


def test_assess_match_uses_pubmed_aware_author_scoring():
    """assess_match must score PubMed ``Lovelace A`` as matching BibTeX (PR #49 Codex P1)."""
    result = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": "Lovelace, A.",
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": "Lovelace A",
            "year": "1843",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_short_surname_display_form_matches_comma_form():
    """``Li, Ada`` ≡ ``Ada Li``; ``Kim, Min`` ≡ ``Min Kim`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("Li, Ada", "Ada Li")
    assert person_lists_equivalent("Kim, Min", "Min Kim")
    result = merge_entries(
        {
            "ID": "li",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Li, Ada",
        },
        {
            "ID": "li",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Ada Li",
        },
        source="crossref",
        confidence=0.95,
    )
    decision = next(item for item in result.decisions if item.field == "author")
    assert decision.normalized_equal
    assert result.substantive == []


def test_accented_given_names_match_latin_initials():
    """``García, J`` ≡ ``García, José``; ``Meyer, MN`` ≡ ``Meyer, Mónica N.`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("García, J", "García, José")
    assert person_lists_equivalent("Meyer, MN", "Meyer, Mónica N.")
    result = merge_entries(
        {
            "ID": "garcia",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "García, J",
        },
        {
            "ID": "garcia",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "García, José",
        },
        source="crossref",
        confidence=0.95,
    )
    decision = next(item for item in result.decisions if item.field == "author")
    assert decision.normalized_equal
    assert result.substantive == []


def test_short_given_name_is_not_compact_initials_for_many_names():
    """``Smith, Amy`` ≠ ``Smith, Alice Mary Yolanda`` (PR #49 Codex P2)."""
    assert not person_lists_equivalent("Smith, Amy", "Smith, Alice Mary Yolanda")
    result = merge_entries(
        {
            "ID": "smith",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Smith, Amy",
        },
        {
            "ID": "smith",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Smith, Alice Mary Yolanda",
        },
        source="crossref",
        confidence=0.95,
    )
    decision = next(item for item in result.decisions if item.field == "author")
    assert not decision.normalized_equal
    assert any(item.field == "author" for item in result.substantive)


def test_comma_ordering_is_not_discarded_by_string_shortcut():
    """``Benjamin, Franklin`` ≠ ``Benjamin Franklin`` (PR #49 Codex P2)."""
    assert not person_lists_equivalent("Benjamin, Franklin", "Benjamin Franklin")


def test_given_token_alignment_is_iterative_for_long_lists():
    """Long given-token lists must not raise RecursionError (PR #49 Codex P2)."""
    many = " ".join(f"Name{i}" for i in range(1200))
    left = f"Family, {many}"
    right = f"Family, {many} Extra"
    assert not person_lists_equivalent(left, right)
