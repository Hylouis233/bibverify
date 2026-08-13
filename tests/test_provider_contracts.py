from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from bibverify.checker import BibTeXChecker
from bibverify.models import QueryStatus

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(provider: str, name: str) -> dict:
    return json.loads((FIXTURES / provider / name).read_text(encoding="utf-8"))


@pytest.fixture
def checker(tmp_path):
    return BibTeXChecker(
        tmp_path / "missing.json",
        overrides={
            "query_settings": {"delay_between_requests": 0},
            "user_info": {"email": "fixture@example.test"},
        },
    )


def original(**extra):
    return {
        "ID": "reliable2026",
        "ENTRYTYPE": "article",
        "title": "Reliable Bibliographic Verification",
        "author": "Ada Lovelace",
        "year": "2026",
        **extra,
    }


def test_crossref_fixture_extracts_candidate_and_doi(checker, requests_mock):
    requests_mock.get("https://api.crossref.org/works", json=load_json("crossref", "search.json"))

    result = checker.provider_registry["crossref"].lookup(original()["title"], original())

    assert result.status is QueryStatus.MATCHED
    assert result.best.entry["doi"] == "10.1000/reliable"


def test_openalex_fixture_extracts_pages_and_provider_status(checker, requests_mock):
    requests_mock.get("https://api.openalex.org/works", json=load_json("openalex", "search.json"))

    result = checker.provider_registry["openalex"].lookup(original()["title"], original())

    assert result.status is QueryStatus.MATCHED
    assert result.best.entry["pages"] == "1--9"
    assert result.to_dict()["status"] == "matched"


def test_semantic_scholar_uses_match_endpoint_and_external_doi(checker, requests_mock):
    route = requests_mock.get(
        "https://api.semanticscholar.org/graph/v1/paper/search/match",
        json=load_json("semantic_scholar", "match.json"),
    )

    result = checker.provider_registry["semantic_scholar"].lookup(original()["title"], original())

    assert route.called
    assert result.status is QueryStatus.MATCHED
    assert result.best.entry["doi"] == "10.1000/reliable"
    assert result.best.entry["pmid"] == "12345678"


def test_pubmed_uses_exact_pmid_without_title_search(checker, requests_mock):
    search = requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        json=load_json("pubmed", "search.json"),
    )
    summary = requests_mock.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        json=load_json("pubmed", "summary.json"),
    )

    result = checker.provider_registry["pubmed"].lookup(
        original(pmid="12345678")["title"], original(pmid="12345678")
    )

    assert not search.called
    assert summary.called
    assert result.status is QueryStatus.MATCHED


def test_europe_pmc_uses_exact_pmcid_query(checker, requests_mock):
    route = requests_mock.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        json=load_json("europe_pmc", "search.json"),
    )

    result = checker.provider_registry["europe_pmc"].lookup(
        original(pmcid="PMC123")["title"], original(pmcid="PMC123")
    )

    assert route.last_request.qs["query"] == ["pmcid:pmc123"]
    assert result.status is QueryStatus.MATCHED


def test_dblp_fixture_normalizes_authors(checker, requests_mock):
    requests_mock.get("https://dblp.org/search/publ/api", json=load_json("dblp", "search.json"))

    result = checker.provider_registry["dblp"].lookup(original()["title"], original())

    assert result.status is QueryStatus.MATCHED
    assert result.best.entry["author"] == "Ada Lovelace"


def test_arxiv_uses_identifier_list_and_does_not_synthesize_doi(checker, requests_mock):
    route = requests_mock.get(
        "https://export.arxiv.org/api/query",
        content=(FIXTURES / "arxiv" / "search.xml").read_bytes(),
    )

    result = checker.provider_registry["arxiv"].lookup(
        original(eprint="2601.00001", archiveprefix="arXiv")["title"],
        original(eprint="2601.00001", archiveprefix="arXiv"),
    )

    assert route.last_request.qs["id_list"] == ["2601.00001"]
    assert result.status is QueryStatus.MATCHED
    assert "doi" not in result.best.entry


def test_biorxiv_title_only_query_is_skipped_without_network(checker, requests_mock):
    result = checker.provider_registry["biorxiv"].lookup(original()["title"], original())

    assert result.status is QueryStatus.SKIPPED
    assert requests_mock.call_count == 0


def test_biorxiv_exact_doi_uses_official_details_route(checker, requests_mock):
    route = requests_mock.get(
        "https://api.biorxiv.org/details/biorxiv/10.1101%2F2026.01.01.123456",
        json=load_json("biorxiv", "details.json"),
    )
    entry = original(doi="10.1101/2026.01.01.123456")

    result = checker.provider_registry["biorxiv"].lookup(entry["title"], entry)

    assert route.called
    assert result.status is QueryStatus.MATCHED
    assert result.best.entry["author"] == "Ada Lovelace and Alan Turing"


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (429, QueryStatus.RATE_LIMITED),
        (401, QueryStatus.AUTH_ERROR),
        (500, QueryStatus.PROVIDER_ERROR),
    ],
)
def test_http_failures_are_not_classified_as_no_match(
    checker, requests_mock, status_code, expected
):
    requests_mock.get("https://api.openalex.org/works", status_code=status_code, text="failed")

    result = checker.provider_registry["openalex"].lookup(original()["title"], original())

    assert result.status is expected
    assert result.status is not QueryStatus.NO_MATCH


def test_invalid_json_is_parse_error(checker, requests_mock):
    requests_mock.get(
        "https://api.openalex.org/works",
        text="not-json",
        headers={"Content-Type": "application/json"},
    )

    result = checker.provider_registry["openalex"].lookup(original()["title"], original())

    assert result.status is QueryStatus.PARSE_ERROR


def test_timeout_is_network_error(checker, requests_mock):
    requests_mock.get("https://api.openalex.org/works", exc=requests.exceptions.Timeout)

    result = checker.provider_registry["openalex"].lookup(original()["title"], original())

    assert result.status is QueryStatus.NETWORK_ERROR


def test_doi_title_conflict_survives_exact_lookup(checker, requests_mock):
    payload = load_json("crossref", "search.json")["message"]["items"][0]
    requests_mock.get(
        "https://api.crossref.org/works/10.1000%2Freliable",
        json={"status": "ok", "message": payload},
    )
    entry = original(title="Unrelated Quantum Gravity Paper", doi="10.1000/reliable")

    result = checker.provider_registry["crossref"].lookup(entry["title"], entry)

    assert result.status is QueryStatus.IDENTIFIER_CONFLICT


def test_exact_doi_404_without_title_is_a_normal_no_match(checker, requests_mock):
    requests_mock.get("https://api.crossref.org/works/10.1000%2Fmissing", status_code=404)
    entry = {"ID": "missing", "doi": "10.1000/missing"}

    result = checker.provider_registry["crossref"].lookup("", entry)

    assert result.status is QueryStatus.NO_MATCH
