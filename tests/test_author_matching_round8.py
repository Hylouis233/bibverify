"""Round-8 Codex regressions for PR #49 author matching."""

from __future__ import annotations

from bibverify._author_names import author_lists_overlap
from bibverify.matching import assess_match, person_lists_equivalent
from bibverify.models import QueryStatus


def test_middle_name_omission_matches_shared_given():
    """``Smith, John`` ≡ ``Smith, John A`` (PR #49 Codex round 8 P1)."""
    assert person_lists_equivalent("Smith, John", "Smith, John A")
    assert person_lists_equivalent("Smith, John A", "Smith, John")
    assert person_lists_equivalent("Smith, John", "Smith, John Adam")
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


def test_bibtex_family_suffix_given_three_part_name():
    """``Smith, Jr, John`` ≡ ``Smith, John Jr`` / ``Smith, John`` (PR #49 Codex round 8 P1)."""
    assert person_lists_equivalent("Smith, Jr, John", "Smith, John Jr")
    assert person_lists_equivalent("Smith, Jr, John", "Smith, John")
    assert not person_lists_equivalent("Smith, Jr, John", "Smith, John Sr")


def test_author_overlap_uses_union_denominator():
    """Partial author overlap uses union size, not max length (PR #49 Codex round 8 P1)."""
    left = "Smith, Alice and Jones, Bob"
    right = "Smith, Alice and Brown, Carol"
    score = author_lists_overlap(left, right)
    assert score is not None
    assert abs(score - 1 / 3) < 1e-9


def test_two_letter_allcaps_given_with_vowel_is_not_letter_split():
    """``Li, BO`` ≠ ``Li, Bob Oliver`` (PR #49 Codex round 8 P2)."""
    assert not person_lists_equivalent("Li, BO", "Li, Bob Oliver")
    assert person_lists_equivalent("Meyer, MN", "Meyer, Michelle N.")
    assert person_lists_equivalent("Smith JR", "Smith, John Robert")


def test_bipartite_matching_is_iterative_for_large_compatible_lists():
    """Large mutually compatible author lists must not RecursionError (PR #49 Codex round 8 P2)."""
    n = 250
    left = " and ".join(f"Author{i}, A" for i in range(n))
    right = " and ".join(f"Author{i}, A" for i in range(n))
    assert author_lists_overlap(left, right) == 1.0


def test_given_token_alignment_allows_optional_extra_middle():
    """Long lists with optional Extra middle must not RecursionError (round 8)."""
    many = " ".join(f"Name{i}" for i in range(1200))
    assert person_lists_equivalent(f"Family, {many}", f"Family, {many} Extra")
    other = " ".join(f"Other{i}" for i in range(1200))
    assert not person_lists_equivalent(f"Family, {many}", f"Family, {other}")


def test_middle_initial_v_optional_under_omission_rules():
    """``V`` stays a middle initial; optional under middle-name omission (round 8)."""
    assert person_lists_equivalent("Smith, John V", "John V Smith")
    assert person_lists_equivalent("Smith, J V", "Smith, John Victor")
    assert person_lists_equivalent("John V Smith", "John Smith")
    assert person_lists_equivalent("Smith, John V", "Smith, John")
