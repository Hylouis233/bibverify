"""Regressions for issue #50: venue leading article + provider reconciliation."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from bibverify.checker import BibTeXChecker
from bibverify.matching import assess_match
from bibverify.merge import merge_entries, normalize_field
from bibverify.models import Candidate, MatchAssessment, ProviderResult, QueryStatus
from bibverify.provider_queries import _prefer_reconciled_candidate, _substantive_mismatch_count

CAMERON_ORIGINAL = {
    "ID": "R17",
    "ENTRYTYPE": "article",
    "author": "Cameron, A. C. and Miller, D. L.",
    "title": "A practitioner's guide to cluster-robust inference",
    "journal": "Journal of Human Resources",
    "year": "2015",
    "volume": "50",
    "number": "2",
    "pages": "317--372",
    "doi": "10.3368/jhr.50.2.317",
}

CROSSREF_MALFORMED = {
    "ID": "R17",
    "ENTRYTYPE": "article",
    "author": "Colin Cameron, A. and Miller, Douglas L.",
    "title": "A Practitioner's Guide to Cluster-Robust Inference",
    "journal": "{The Journal of Human Resources}",
    "year": "2015",
    "volume": "50",
    "number": "2",
    "pages": "317--372",
    "doi": "10.3368/jhr.50.2.317",
}

OPENALEX_CLEAN = {
    "ID": "R17",
    "ENTRYTYPE": "article",
    "author": "A. Colin Cameron and Douglas L. Miller",
    "title": "A Practitioner's Guide to Cluster-Robust Inference",
    "journal": "{The Journal of Human Resources}",
    "year": "2015",
    "volume": "50",
    "number": "2",
    "pages": "317--372",
    "doi": "10.3368/jhr.50.2.317",
}


def test_venue_leading_the_is_equivalent_including_braces():
    """``Journal of Human Resources`` ≡ ``{The Journal of Human Resources}`` (#50)."""
    plain = "Journal of Human Resources"
    with_the = "The Journal of Human Resources"
    braced = "{The Journal of Human Resources}"
    assert normalize_field("journal", plain) == normalize_field("journal", with_the)
    assert normalize_field("journal", plain) == normalize_field("journal", braced)
    assert normalize_field("journal", plain) == "journal of human resources"

    result = merge_entries(
        {"ID": "jhr", "ENTRYTYPE": "article", "journal": plain},
        {"ID": "jhr", "ENTRYTYPE": "article", "journal": braced},
        source="crossref",
        confidence=0.99,
    )
    decision = next(item for item in result.decisions if item.field == "journal")
    assert decision.normalized_equal
    assert decision.action == "keep_original"
    assert result.substantive == []


def test_venue_leading_a_and_an_are_equivalent_for_booktitle():
    assert normalize_field("booktitle", "International Conference on ML") == normalize_field(
        "booktitle", "An International Conference on ML"
    )
    assert normalize_field("journal", "Journal of Foo") == normalize_field(
        "journal", "A Journal of Foo"
    )
    # Middle articles must not be stripped.
    assert "the" in normalize_field("journal", "Journal of the Royal Society")


def test_distinct_venue_names_remain_substantive():
    result = merge_entries(
        {"ID": "x", "ENTRYTYPE": "article", "journal": "Journal of Human Resources"},
        {"ID": "x", "ENTRYTYPE": "article", "journal": "Journal of Economic Literature"},
        source="crossref",
        confidence=0.99,
    )
    decision = next(item for item in result.decisions if item.field == "journal")
    assert not decision.normalized_equal
    assert any(item.field == "journal" for item in result.substantive)


def test_openalex_author_form_matches_bibtex_initials():
    """OpenAlex ``A. Colin Cameron`` ≡ BibTeX ``Cameron, A. C.`` (#50 case A)."""
    result = merge_entries(
        CAMERON_ORIGINAL,
        OPENALEX_CLEAN,
        source="openalex",
        confidence=0.99,
    )
    author = next(item for item in result.decisions if item.field == "author")
    journal = next(item for item in result.decisions if item.field == "journal")
    assert author.normalized_equal
    assert author.action == "keep_original"
    assert journal.normalized_equal
    assert journal.action == "keep_original"
    assert result.substantive == []


def test_crossref_malformed_author_alone_is_still_substantive():
    """Crossref ``Colin Cameron, A.`` alone must not silently match (#50 case A)."""
    result = merge_entries(
        CAMERON_ORIGINAL,
        CROSSREF_MALFORMED,
        source="crossref",
        confidence=0.99,
    )
    author = next(item for item in result.decisions if item.field == "author")
    journal = next(item for item in result.decisions if item.field == "journal")
    assert journal.normalized_equal  # venue The-equivalence
    assert not author.normalized_equal
    assert any(item.field == "author" for item in result.substantive)


def test_prefer_reconciled_candidate_picks_openalex_over_crossref():
    """Among matched providers, prefer the one that does not hard-fail authors."""
    assessment = MatchAssessment(
        0.99,
        QueryStatus.MATCHED,
        {"title": 1.0, "identifier_exact": True},
        "fixture",
    )
    crossref = Candidate("crossref", CROSSREF_MALFORMED, assessment)
    openalex = Candidate("openalex", OPENALEX_CLEAN, assessment)
    assert _substantive_mismatch_count(CAMERON_ORIGINAL, crossref) > 0
    assert _substantive_mismatch_count(CAMERON_ORIGINAL, openalex) == 0
    preferred = _prefer_reconciled_candidate(CAMERON_ORIGINAL, [crossref, openalex])
    assert preferred.provider == "openalex"


def _make_checker(tmp_path: Path) -> BibTeXChecker:
    bib = tmp_path / "references.bib"
    bib.write_text("@article{R17, title={Demo}, year={2015}}\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "language": "EN",
                "bib_file": bib.name,
                "query_settings": {
                    "delay_between_requests": 0,
                    "stop_on_first_match": True,
                },
                "platforms": {
                    "crossref": {"enabled": True, "priority": 1},
                    "openalex": {"enabled": True, "priority": 2},
                    "semantic_scholar": {"enabled": False},
                    "pubmed": {"enabled": False},
                    "europe_pmc": {"enabled": False},
                    "dblp": {"enabled": False},
                    "arxiv": {"enabled": False},
                    "biorxiv": {"enabled": False},
                },
            }
        ),
        encoding="utf-8",
    )
    return BibTeXChecker(config, dry_run=True)


def test_stop_on_first_continues_past_dirty_crossref_to_openalex(tmp_path):
    """Default stop-on-first must not hard-fail when a later provider reconciles (#50)."""
    checker = _make_checker(tmp_path)
    queried: list[str] = []

    class FakeProvider:
        def __init__(self, name: str, entry: dict):
            self.name = name
            self.entry = entry

        def lookup(self, title: str, entry: dict) -> ProviderResult:
            queried.append(self.name)
            assessment = assess_match(entry, self.entry)
            candidate = Candidate(self.name, self.entry, assessment)
            return ProviderResult(self.name, assessment.status, [candidate])

    checker.provider_registry = {
        "crossref": FakeProvider("crossref", CROSSREF_MALFORMED),
        "openalex": FakeProvider("openalex", OPENALEX_CLEAN),
    }
    checker.enabled_platforms = ["crossref", "openalex"]

    with redirect_stdout(StringIO()):
        outcome = checker.query_multi_platform_result(CAMERON_ORIGINAL["title"], CAMERON_ORIGINAL)

    assert queried == ["crossref", "openalex"]
    assert outcome.best_candidate is not None
    assert outcome.best_candidate.provider == "openalex"
    merged = merge_entries(
        CAMERON_ORIGINAL,
        outcome.best_candidate.entry,
        source=outcome.best_candidate.provider,
        confidence=outcome.best_candidate.confidence,
    )
    assert merged.substantive == []


def test_stop_on_first_still_stops_when_first_provider_is_clean(tmp_path):
    """Clean first hits must still honor stop_on_first_match (no extra queries)."""
    checker = _make_checker(tmp_path)
    queried: list[str] = []

    class FakeProvider:
        def __init__(self, name: str, entry: dict):
            self.name = name
            self.entry = entry

        def lookup(self, title: str, entry: dict) -> ProviderResult:
            queried.append(self.name)
            assessment = assess_match(entry, self.entry)
            candidate = Candidate(self.name, self.entry, assessment)
            return ProviderResult(self.name, assessment.status, [candidate])

    checker.provider_registry = {
        "crossref": FakeProvider("crossref", OPENALEX_CLEAN),
        "openalex": FakeProvider("openalex", OPENALEX_CLEAN),
    }
    checker.enabled_platforms = ["crossref", "openalex"]

    with redirect_stdout(StringIO()):
        outcome = checker.query_multi_platform_result(CAMERON_ORIGINAL["title"], CAMERON_ORIGINAL)

    assert queried == ["crossref"]
    assert outcome.best_candidate is not None
    assert outcome.best_candidate.provider == "crossref"
