"""Regressions for Codex author-matching follow-ups on PR #48 / #49."""

from __future__ import annotations

from bibverify.matching import (
    assess_match,
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


def test_compact_initials_match_expanded_given_names():
    """``Meyer, M.N.`` ≡ ``Meyer, Michelle N.`` (PR #48 Codex P2; undotted MN is a given)."""
    result = merge_entries(
        {
            "ID": "meyer",
            "ENTRYTYPE": "article",
            "title": "Demo",
            "author": "Meyer, M.N.",
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
    """``García, J`` ≡ ``García, José``; ``Meyer, M.N.`` ≡ ``Meyer, Mónica N.`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("García, J", "García, José")
    assert person_lists_equivalent("Meyer, M.N.", "Meyer, Mónica N.")
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
    """Long given-token lists must not RecursionError (PR #49 Codex P2 / round 8)."""
    many = " ".join(f"Name{i}" for i in range(1200))
    # Identical long lists stay equivalent without deep recursion.
    assert person_lists_equivalent(f"Family, {many}", f"Family, {many}")
    # Trailing Extra is optional middle under middle-name omission rules.
    assert person_lists_equivalent(f"Family, {many}", f"Family, {many} Extra")
    other = " ".join(f"Other{i}" for i in range(1200))
    assert not person_lists_equivalent(f"Family, {many}", f"Family, {other}")


def test_pubmed_jr_initials_are_not_blocked_as_suffix():
    """PubMed ``Smith JR`` ≡ ``Smith, John Robert`` (PR #49 Codex round 3 P1)."""
    assert person_lists_equivalent("Smith JR", "Smith, John Robert")
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, John Robert",
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith JR",
            "year": "2020",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_mixed_list_comma_checked_per_author():
    """List-level comma must not hide a per-author family swap (PR #49 Codex round 3 P2)."""
    assert not person_lists_equivalent(
        "Smith, John and Benjamin, Franklin",
        "Smith, John and Benjamin Franklin",
    )


def test_dotted_cyrillic_initial_matches_expanded_given_name():
    """``Иванов, И.`` ≡ ``Иванов, Иван``; undotted CJK still not initials (PR #49 Codex round 3 P2)."""
    assert person_lists_equivalent("Иванов, И.", "Иванов, Иван")
    assert not person_lists_equivalent("王, 伟", "王, 伟明")


def test_middle_initial_v_is_not_stripped_as_roman_numeral():
    """``Smith, John V`` ≡ ``John V Smith``; V is a middle initial (PR #49)."""
    assert person_lists_equivalent("Smith, John V", "John V Smith")
    assert person_lists_equivalent("Smith, J V", "Smith, John Victor")
    # Under middle-name omission, bare John may omit middle V.
    assert person_lists_equivalent("Smith, John V", "Smith, John")
    assert person_lists_equivalent("John V Smith", "John Smith")


def test_middle_name_omission_assess_match_matched():
    """``Smith, John`` vs ``Smith, John A`` same title/year → MATCHED (PR #49 P1 / round 9)."""
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, John",
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, John A",
            "year": "2020",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_one_letter_surname_display_form_matches_comma_form():
    """``O, Jane`` ≡ ``Jane O`` (PR #49 Codex round 9 P2)."""
    assert person_lists_equivalent("O, Jane", "Jane O")
    assert person_lists_equivalent("Jane O", "O, Jane")
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": "O, Jane",
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Jane O",
            "year": "2020",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_undotted_two_letter_given_is_not_letter_split():
    """``Nguyen, MY`` ≢ ``Nguyen, Mary Yolanda`` (PR #49 Codex round 9 P2)."""
    assert not person_lists_equivalent("Nguyen, MY", "Nguyen, Mary Yolanda")
    # Dotted / spaced compact initials still expand.
    assert person_lists_equivalent("Meyer, M.N.", "Meyer, Michelle N.")
    assert person_lists_equivalent("Meyer, M N", "Meyer, Michelle N.")
    # No-comma PubMed packs remain initials.
    assert person_lists_equivalent("Meyer MN", "Meyer, Michelle N.")


def test_dotted_degree_title_is_not_compact_initials():
    """``Smith M.D.`` ≢ ``Smith, Mary Davis`` (PR #49 Codex round 9 P2)."""
    assert not person_lists_equivalent("Smith M.D.", "Smith, Mary Davis")
    assert not person_lists_equivalent("Smith Ph.D.", "Smith, Peter Harold David")
    # Dotted initial runs that are not credentials still work.
    assert person_lists_equivalent("Smith M.N.", "Smith, Mary Nancy")


def test_bibtex_explicit_suffix_v_matches_middle_v():
    """``Smith, V, John`` ≡ ``Smith, John V`` (PR #49 Codex round 9 P2)."""
    assert person_lists_equivalent("Smith, V, John", "Smith, John V")
    assert person_lists_equivalent("Smith, V, John", "John V Smith")
    assert person_lists_equivalent("Smith, V, John", "Smith, John")


def test_family_only_matches_same_family_with_given():
    """``Smith, John`` ≡ bare ``Smith``; Crossref family-only (PR #49 Codex round 10 P1)."""
    assert person_lists_equivalent("Smith, John", "Smith")
    assert person_lists_equivalent("Smith", "Smith, John")
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, John",
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith",
            "year": "2020",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_family_only_does_not_match_conflicting_given():
    """``Smith, John`` ≢ ``Smith, Mary`` even with shared family (PR #49 Codex round 10 P1)."""
    assert not person_lists_equivalent("Smith, John", "Smith, Mary")
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, John",
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, Mary",
            "year": "2020",
        },
    )
    assert result.signals["authors"] != 1.0
