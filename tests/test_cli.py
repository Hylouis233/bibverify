import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from bibverify.cli import _translate_legacy_args, app

runner = CliRunner()


def test_help_exposes_modern_command_groups():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ["check", "doi", "config", "doctor", "providers", "mcp"]:
        assert command in result.stdout


def test_providers_json_is_machine_readable():
    result = runner.invoke(app, ["providers", "list", "--json"])

    assert result.exit_code == 0
    assert "crossref" in json.loads(result.stdout)["providers"]


def test_config_init_round_trip(tmp_path):
    output = tmp_path / "配置.json"

    result = runner.invoke(app, ["config", "init", "--output", str(output)])

    assert result.exit_code == 0
    assert output.exists()


def test_check_json_keeps_progress_off_stdout(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text("@article{demo, title={Demo}, year={2026}}\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"bib_file": bib.name}), encoding="utf-8")
    summary = {
        "counts": {"total": 1, "verified": 1, "updated": 0, "not_found": 0, "errors": 0},
        "files": {},
    }

    with patch("bibverify.cli.BibTeXChecker") as checker_class:
        checker_class.return_value.run.return_value = summary
        result = runner.invoke(app, ["check", "--config", str(config), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["counts"]["verified"] == 1


def test_cli_path_overrides_resolve_from_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    summary = {
        "counts": {"total": 0, "verified": 0, "updated": 0, "not_found": 0, "errors": 0},
        "files": {},
    }

    with patch("bibverify.cli.BibTeXChecker") as checker_class:
        checker_class.return_value.run.return_value = summary
        result = runner.invoke(
            app,
            ["check", "relative/references.bib", "--output-dir", "relative/output", "--json"],
        )

    assert result.exit_code == 0
    overrides = checker_class.call_args.kwargs["overrides"]
    assert Path(overrides["bib_file"]) == (tmp_path / "relative/references.bib").resolve()
    assert Path(overrides["output_dir"]) == (tmp_path / "relative/output").resolve()


def test_legacy_cli_forms_are_translated():
    assert _translate_legacy_args(["config.json"]) == ["check", "--config", "config.json"]
    assert _translate_legacy_args(["config.json", "--doi", "10.1/test", "--key", "demo"]) == [
        "doi",
        "10.1/test",
        "--config",
        "config.json",
        "--key",
        "demo",
    ]
