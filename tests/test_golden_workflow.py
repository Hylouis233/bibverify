from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import bibtexparser

from bibverify.checker import BibTeXChecker
from bibverify.models import (
    Candidate,
    EntryStatus,
    MatchAssessment,
    ProviderResult,
    QueryOutcome,
    QueryStatus,
)


def make_project(tmp_path: Path, *, report_format: str = "json") -> tuple[Path, Path, bytes]:
    bib = tmp_path / "references.bib"
    raw = (
        "@article{demo2026,\r\n"
        "  title = {Old Metadata Title},\r\n"
        "  author = {Lovelace, Ada},\r\n"
        "  year = {2025},\r\n"
        "  doi = {https://doi.org/10.1000/RELIABLE},\r\n"
        "  abstract = {A user-maintained abstract with 中文 and café.},\r\n"
        "  keywords = {metadata; verification},\r\n"
        "  file = {papers/demo.pdf},\r\n"
        "  urldate = {2026-08-13},\r\n"
        "  x_custom = {preserve this}\r\n"
        "}\r\n"
    ).encode()
    bib.write_bytes(raw)
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "language": "EN",
                "bib_file": bib.name,
                "output_dir": "output",
                "query_settings": {"delay_between_requests": 0},
                "output_settings": {
                    "timestamp_format": "fixed",
                    "report_format": report_format,
                },
            }
        ),
        encoding="utf-8",
    )
    return bib, config, raw


def matched_outcome(entry: dict) -> QueryOutcome:
    candidate_entry = {
        "ID": entry["ID"],
        "ENTRYTYPE": "article",
        "title": "{Reliable Bibliographic Verification}",
        "author": "Lovelace, Ada",
        "year": "2026",
        "doi": "10.1000/reliable",
        "journal": "{Journal of Metadata}",
    }
    assessment = MatchAssessment(
        0.98,
        QueryStatus.MATCHED,
        {"title": 0.94, "identifier_exact": True},
        "Fixture candidate.",
    )
    candidate = Candidate("crossref", candidate_entry, assessment, payload={})
    provider = ProviderResult("crossref", QueryStatus.MATCHED, [candidate], elapsed_ms=1)
    return QueryOutcome(
        EntryStatus.VERIFIED,
        [provider],
        candidate,
        complete=True,
        reason="Fixture verified.",
    )


def run_fixture(config: Path, *, dry_run: bool = False, apply_changes: bool = False):
    checker = BibTeXChecker(config, dry_run=dry_run, apply_changes=apply_changes)
    checker.query_multi_platform_result = lambda title, entry: matched_outcome(entry)
    with redirect_stdout(StringIO()):
        summary = checker.run()
    return checker, summary


def parse_one(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as stream:
        database = bibtexparser.load(stream)
    assert len(database.entries) == 1
    return database.entries[0]


def test_default_run_never_modifies_input_and_preserves_custom_fields(tmp_path):
    bib, config, raw = make_project(tmp_path)

    _, summary = run_fixture(config)

    assert bib.read_bytes() == raw
    updated = Path(summary["files"]["updated"])
    parsed = parse_one(updated)
    assert parsed["title"] == "{Reliable Bibliographic Verification}"
    assert parsed["abstract"] == "A user-maintained abstract with 中文 and café."
    assert parsed["keywords"] == "metadata; verification"
    assert parsed["file"] == "papers/demo.pdf"
    assert parsed["urldate"] == "2026-08-13"
    assert parsed["x_custom"] == "preserve this"
    assert parsed["doi"] == "https://doi.org/10.1000/RELIABLE"
    assert "{{{" not in updated.read_text(encoding="utf-8")
    assert summary["counts"]["updated"] == 1
    assert summary["complete"] is True


def test_dry_run_writes_nothing(tmp_path):
    bib, config, raw = make_project(tmp_path)

    checker, summary = run_fixture(config, dry_run=True)

    assert bib.read_bytes() == raw
    assert not (tmp_path / "output").exists()
    assert summary["dry_run"] is True
    assert all(value is None for value in summary["files"].values())
    assert checker.http.cache is None


def test_apply_backs_up_then_updates_input_non_destructively(tmp_path):
    bib, config, raw = make_project(tmp_path)

    _, summary = run_fixture(config, apply_changes=True)

    backup = Path(summary["files"]["backup"])
    assert backup.read_bytes() == raw
    assert summary["applied"] is True
    assert Path(summary["files"]["applied"]) == bib.resolve()
    parsed = parse_one(bib)
    assert parsed["title"] == "{Reliable Bibliographic Verification}"
    assert parsed["abstract"] == "A user-maintained abstract with 中文 and café."
    assert parsed["x_custom"] == "preserve this"
    assert parsed["doi"] == "https://doi.org/10.1000/RELIABLE"


def test_json_report_contains_field_provenance_and_completion(tmp_path):
    _, config, _ = make_project(tmp_path, report_format="json")

    _, summary = run_fixture(config)

    report = json.loads(Path(summary["files"]["report"]).read_text(encoding="utf-8"))
    assert report["schema_version"] == "1.0"
    assert report["complete"] is True
    entry = report["entries"][0]
    title_diff = next(diff for diff in entry["field_diffs"] if diff["field"] == "title")
    assert title_diff["source"] == "crossref"
    assert title_diff["confidence"] == 0.98
    assert title_diff["action"] == "update"


def test_source_failure_is_incomplete_not_not_found(tmp_path):
    _, config, _ = make_project(tmp_path)
    checker = BibTeXChecker(config, dry_run=True)

    def unavailable(title, entry):
        provider = ProviderResult("crossref", QueryStatus.NETWORK_ERROR, error="connection failed")
        return QueryOutcome(
            EntryStatus.SOURCE_UNAVAILABLE,
            [provider],
            complete=False,
            reason="Verification incomplete.",
        )

    checker.query_multi_platform_result = unavailable
    with redirect_stdout(StringIO()):
        summary = checker.run()

    assert summary["complete"] is False
    assert summary["counts"]["source_unavailable"] == 1
    assert summary["counts"]["not_found"] == 0
    assert summary["entries"][0]["provider_status"][0]["status"] == "network_error"
