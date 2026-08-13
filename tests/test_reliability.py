from __future__ import annotations

from bibverify.identifiers import extract_identifiers
from bibverify.matching import assess_match, title_similarity
from bibverify.merge import merge_entries
from bibverify.models import QueryStatus


def test_identifier_extraction_handles_common_wrappers():
    identifiers = extract_identifiers(
        {
            "doi": "https://doi.org/10.1000/XYZ.",
            "url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7654321/",
            "eprint": "arXiv:2401.12345v2",
        }
    )

    assert identifiers.doi == "10.1000/xyz"
    assert identifiers.pmid == "12345678"
    assert identifiers.pmcid == "PMC7654321"
    assert identifiers.arxiv == "2401.12345"


def test_short_title_does_not_match_incidental_substring():
    assert title_similarity("AI", "A survey of explainable AI systems") < 0.68


def test_multi_signal_match_accepts_title_author_and_year_agreement():
    result = assess_match(
        {
            "title": "Detecting Influenza Epidemics using Search Engine Query Data",
            "author": "Ginsberg, Jeremy and Mohebbi, Matthew",
            "year": "2009",
        },
        {
            "title": "Detecting influenza epidemics using search-engine query data",
            "author": "Jeremy Ginsberg and Matthew Mohebbi",
            "year": "2009",
        },
    )

    assert result.status is QueryStatus.MATCHED
    assert result.score >= 0.86


def test_exact_doi_with_materially_different_title_is_identifier_conflict():
    result = assess_match(
        {"title": "A study of influenza", "doi": "10.1000/example"},
        {"title": "Quantum gravity in black holes", "doi": "10.1000/example"},
    )

    assert result.status is QueryStatus.IDENTIFIER_CONFLICT
    assert result.signals["identifier_exact"] is True


def test_different_dois_are_never_treated_as_a_match():
    result = assess_match(
        {"title": "Same title", "doi": "10.1000/one"},
        {"title": "Same title", "doi": "10.1000/two"},
    )

    assert result.status is QueryStatus.IDENTIFIER_CONFLICT


def test_exact_identifier_can_fill_a_missing_input_title():
    result = assess_match(
        {"doi": "10.1000/example"},
        {"title": "Reliable Bibliographic Verification", "doi": "10.1000/example"},
    )

    assert result.status is QueryStatus.MATCHED
    assert result.signals["identifier_exact"] is True


def test_exact_title_without_supporting_signals_is_ambiguous():
    result = assess_match(
        {"title": "Reliable Bibliographic Verification"},
        {"title": "Reliable Bibliographic Verification"},
    )

    assert result.status is QueryStatus.AMBIGUOUS
    assert "Title agreement alone" in result.reason


def test_merge_preserves_custom_fields_and_missing_provider_fields():
    original = {
        "ID": "demo",
        "ENTRYTYPE": "article",
        "title": "Old title",
        "year": "2020",
        "abstract": "User abstract",
        "keywords": "one; two",
        "file": "paper.pdf",
        "custom": "keep me",
    }
    result = merge_entries(
        original,
        {"ID": "demo", "ENTRYTYPE": "article", "title": "Correct title", "year": "2021"},
        source="crossref",
        confidence=0.98,
    )

    assert result.entry["title"] == "Correct title"
    assert result.entry["abstract"] == "User abstract"
    assert result.entry["keywords"] == "one; two"
    assert result.entry["file"] == "paper.pdf"
    assert result.entry["custom"] == "keep me"


def test_merge_never_overwrites_a_conflicting_identifier():
    result = merge_entries(
        {"ID": "demo", "ENTRYTYPE": "article", "doi": "10.1000/one"},
        {"ID": "demo", "ENTRYTYPE": "article", "doi": "10.1000/two"},
        source="crossref",
        confidence=1.0,
    )

    assert result.entry["doi"] == "10.1000/one"
    decision = next(item for item in result.decisions if item.field == "doi")
    assert decision.action == "manual_review"


def test_normalized_doi_is_kept_verbatim():
    result = merge_entries(
        {"ID": "demo", "ENTRYTYPE": "article", "doi": "https://doi.org/10.1000/ABC"},
        {"ID": "demo", "ENTRYTYPE": "article", "doi": "10.1000/abc"},
        source="crossref",
        confidence=1.0,
    )

    assert result.entry["doi"] == "https://doi.org/10.1000/ABC"
    decision = next(item for item in result.decisions if item.field == "doi")
    assert decision.normalized_equal is True
    assert decision.action == "keep_original"
