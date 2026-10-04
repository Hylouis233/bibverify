"""Exercise process exit handling and JSON output outside Typer's UTF-8 runner."""

import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from bibverify.cli import main
from bibverify.models import ProviderResult, QueryStatus


@pytest.mark.parametrize(
    ("counts", "complete", "expected"),
    [
        ({"verified": 1}, True, 0),
        ({"updated": 1}, True, 2),
        ({"ambiguous": 1}, True, 3),
        ({"not_found": 1}, True, 3),
        ({"identifier_conflict": 1}, True, 3),
        ({"source_unavailable": 1}, True, 4),
        ({"errors": 1}, True, 4),
        ({}, False, 4),
        ({"invalid_input": 1}, True, 5),
        ({"updated": 1, "identifier_conflict": 1}, True, 3),
        ({"updated": 1, "source_unavailable": 1}, True, 4),
        ({"invalid_input": 1, "source_unavailable": 1}, True, 5),
    ],
)
def test_main_propagates_check_semantic_exit_codes(counts, complete, expected):
    with patch("bibverify.cli.BibTeXChecker") as checker_class:
        checker_class.return_value.run.return_value = {"counts": counts, "complete": complete}
        assert main(["check", "--quiet"]) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (QueryStatus.NO_MATCH, 1),
        (QueryStatus.IDENTIFIER_CONFLICT, 3),
        (QueryStatus.NETWORK_ERROR, 4),
        (QueryStatus.INVALID_INPUT, 5),
    ],
)
def test_main_propagates_doi_exit_codes(status, expected):
    with patch("bibverify.cli.BibTeXChecker") as checker_class:
        checker = checker_class.return_value
        checker.bibtex_from_doi_result.return_value = (None, ProviderResult("crossref", status))
        checker.doi_lookup_failure_message.return_value = "Lookup failed"
        assert main(["doi", "10.1000/example"]) == expected


def test_main_keeps_usage_error_exit_code():
    assert main(["check", "--dry-run", "--apply"]) == 2


@pytest.mark.parametrize("legacy", [False, True])
def test_process_entrypoints_exit_nonzero_for_missing_input(tmp_path, legacy):
    repo_root = Path(__file__).resolve().parents[1]
    entrypoint = [str(repo_root / "bib_check.py")] if legacy else ["-m", "bibverify"]
    result = subprocess.run(
        [sys.executable, *entrypoint, "check", str(tmp_path / "missing.bib"), "--dry-run"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 5
    assert "Error:" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("command", ["check", "doi", "doctor", "benchmark"])
def test_json_round_trips_through_legacy_console_encoding(command, monkeypatch):
    # U+2010 and CJK text are not representable in a legacy Windows cp1252 stream.
    label = "Encoding\u2010canary \u4e2d\u6587"
    if command == "check":
        target = "bibverify.cli.BibTeXChecker"
        args = ["check", "--json"]
        expected = {"counts": {}, "title": label}
    elif command == "doi":
        target = "bibverify.cli.BibTeXChecker"
        args = ["doi", "10.1000/example", "--json"]
        expected = {"doi": "10.1000/example", "bibtex": label}
    elif command == "doctor":
        target = "bibverify.cli.doctor"
        args = ["doctor", "--json"]
        expected = [{"ok": True, "required": True, "message": label}]
    else:
        target = "bibverify.cli.run_benchmark"
        args = ["benchmark"]
        expected = {"wrong_auto_match_rate": 0, "label": label}

    sink = io.BytesIO()
    stdout = io.TextIOWrapper(sink, encoding="cp1252", write_through=True)
    with patch(target) as mocked, monkeypatch.context() as context:
        if command == "check":
            mocked.return_value.run.return_value = expected
        elif command == "doi":
            mocked.return_value.bibtex_from_doi_result.return_value = (
                label,
                ProviderResult("crossref", QueryStatus.MATCHED),
            )
            mocked.return_value.canonicalize_doi.return_value = "10.1000/example"
        else:
            mocked.return_value = expected
        context.setattr(sys, "stdout", stdout)
        assert main(args) == 0

    assert json.loads(sink.getvalue().decode("cp1252")) == expected
