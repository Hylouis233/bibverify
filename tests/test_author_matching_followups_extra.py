"""Regressions for Codex author-matching follow-ups on PR #48 / #49."""

from __future__ import annotations

from bibverify.matching import (
    assess_match,
    expand_abbreviated_page_range,
    person_lists_equivalent,
)
from bibverify.models import QueryStatus


def test_allcaps_short_surname_after_given_name_is_family():
    """``Li, Ada`` ≡ ``Ada LI`` / ``Ng, Ada`` ≡ ``Ada NG`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("Li, Ada", "Ada LI")
    assert person_lists_equivalent("Wu, Ada", "Ada WU")
    assert person_lists_equivalent("Kim, Min", "Min KIM")
    assert person_lists_equivalent("Lee, Jane", "Jane LEE")
    assert person_lists_equivalent("Ng, Ada", "Ada NG")
    assert not person_lists_equivalent("Ada LI", "Bob LI")
    result = assess_match(
        {"title": "Notes on the Analytical Engine", "author": "Li, Ada", "year": "1843"},
        {"title": "Notes on the Analytical Engine", "author": "Ada LI", "year": "1843"},
    )
    assert result.signals["authors"] == 1.0
    ng = assess_match(
        {"title": "Notes on the Analytical Engine", "author": "Ng, Ada", "year": "1843"},
        {"title": "Notes on the Analytical Engine", "author": "Ada NG", "year": "1843"},
    )
    assert ng.signals["authors"] == 1.0


def test_pubmed_initial_blocks_still_parse_as_initials():
    """Vowel-free and suffix-like PubMed blocks stay initials after the P1 fix."""
    assert person_lists_equivalent("Smith, John Robert", "Smith JR")
    assert person_lists_equivalent("Smith, S R", "Smith SR")
    assert person_lists_equivalent("Meyer, M.N.", "Meyer, Michelle N.")
    assert person_lists_equivalent("Meyer, P M", "Meyer PM")
    assert person_lists_equivalent("Lovelace, A.", "Lovelace A")
    # Vowel-bearing initials remain acceptable via the alternate PubMed reading.
    assert person_lists_equivalent("Lovelace, Ada M.", "Lovelace AM")


def test_sole_given_token_is_not_stripped_as_suffix():
    """``Smith, V`` ≡ ``Smith, Victor``; ``Md Rahman`` ≢ ``Rahman`` (PR #49 Codex P2)."""
    assert person_lists_equivalent("Smith, V", "Smith, Victor")
    assert not person_lists_equivalent("Smith, V", "Smith, William")
    assert not person_lists_equivalent("Md Rahman", "Rahman")
    assert person_lists_equivalent("Rahman, Md", "Md Rahman")
    assert person_lists_equivalent("Smith, J V", "Smith, John Victor")
    assert person_lists_equivalent("Smith, Victor Jr", "Smith, Victor")


def test_page_range_helper_is_reexported_from_matching():
    """``expand_abbreviated_page_range`` stays importable from ``bibverify.matching``."""
    assert expand_abbreviated_page_range("683--97") == "683-697"


def test_scoring_uses_alternate_pubmed_family_parse():
    """``Lovelace AM`` must score against ``Lovelace, Ada Mary`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("Lovelace, Ada Mary", "Lovelace AM")
    result = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": "Lovelace, Ada Mary",
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": "Lovelace AM",
            "year": "1843",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_pubmed_dotted_and_spaced_initial_runs_keep_family():
    """``Smith M.N.`` / ``Smith M. N.`` ≡ ``Smith, Mary Nancy`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("Smith M.N.", "Smith, Mary Nancy")
    assert person_lists_equivalent("Smith M. N.", "Smith, Mary Nancy")
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith, Mary Nancy",
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": "Smith M.N.",
            "year": "2020",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_scoring_requires_full_person_compatibility():
    """Family-only alternate overlap must not score ``Ada, Bob`` vs ``Ada LI`` (PR #49 Codex P1)."""
    assert not person_lists_equivalent("Ada, Bob", "Ada LI")
    result = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": "Ada, Bob",
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": "Ada LI",
            "year": "1843",
        },
    )
    assert result.signals["authors"] == 0.0
    assert result.status != QueryStatus.MATCHED


def test_leading_initials_support_allcaps_surname():
    """``Ng, A. B.`` ≡ ``A. B. NG`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("Ng, A. B.", "A. B. NG")
    result = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": "Ng, A. B.",
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": "A. B. NG",
            "year": "1843",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_undotted_allcaps_given_name_is_not_letter_split():
    """``Li, ADA`` ≠ ``Li, Alice Diana Anne`` (PR #49 Codex P2)."""
    assert not person_lists_equivalent("Li, ADA", "Li, Alice Diana Anne")


def test_author_overlap_is_order_independent():
    """Reordered equal-length author lists still fully agree (PR #49 Codex P2)."""
    left = "Smith, Alice and Jones, Bob"
    right = "Jones, Bob and Smith, Alice"
    assert person_lists_equivalent(
        "Smith, Alice",
        "Smith, Alice",
    )
    result = assess_match(
        {
            "title": "A Study of Something Interesting Enough",
            "author": left,
            "year": "2020",
        },
        {
            "title": "A Study of Something Interesting Enough",
            "author": right,
            "year": "2020",
        },
    )
    assert result.signals["authors"] == 1.0


def test_collapsed_shortcut_preserves_comma_family_boundary():
    """``Smith A, B`` ≠ ``Smith, A B`` (PR #49 Codex P2)."""
    assert not person_lists_equivalent("Smith A, B", "Smith, A B")


def test_author_overlap_uses_maximum_bipartite_matching():
    """Ambiguous ``Ada LI`` must not make overlap depend on author order (PR #49 Codex P1)."""
    left = "Ada LI and Ada, Laura Irene"
    right_a = "Ada, Laura Irene and Li, Ada"
    right_b = "Li, Ada and Ada, Laura Irene"
    from bibverify._author_names import author_lists_overlap

    assert author_lists_overlap(left, right_a) == 1.0
    assert author_lists_overlap(left, right_b) == 1.0
    result_a = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": left,
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": right_a,
            "year": "1843",
        },
    )
    result_b = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": left,
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": right_b,
            "year": "1843",
        },
    )
    assert result_a.signals["authors"] == 1.0
    assert result_b.signals["authors"] == 1.0


def test_allcaps_full_given_supports_given_family_parse():
    """``LI, ADA`` ≡ ``ADA LI`` / ``Ada LI`` (PR #49 Codex P1)."""
    assert person_lists_equivalent("LI, ADA", "ADA LI")
    assert person_lists_equivalent("LI, ADA", "Ada LI")
    assert person_lists_equivalent("ADA LI", "Ada LI")
    result = assess_match(
        {
            "title": "Notes on the Analytical Engine",
            "author": "LI, ADA",
            "year": "1843",
        },
        {
            "title": "Notes on the Analytical Engine",
            "author": "ADA LI",
            "year": "1843",
        },
    )
    assert result.signals["authors"] == 1.0
    assert result.status == QueryStatus.MATCHED


def test_conflicting_generational_suffixes_are_not_equivalent():
    """``Jr`` vs ``Sr`` / ``II`` vs ``III`` stay distinct; bare may omit (PR #49 Codex P2)."""
    assert not person_lists_equivalent("Smith, John Jr", "Smith, John Sr")
    assert not person_lists_equivalent("Smith, John II", "Smith, John III")
    assert person_lists_equivalent("Smith, John Jr", "Smith, John")
    assert person_lists_equivalent("Smith, Victor Jr", "Smith, Victor")
