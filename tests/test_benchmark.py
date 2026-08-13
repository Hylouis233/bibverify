import json
from pathlib import Path

from typer.testing import CliRunner

from bibverify.benchmark import run_benchmark
from bibverify.cli import app

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_has_no_wrong_automatic_matches():
    result = run_benchmark(ROOT / "benchmarks" / "cases.json")

    assert result["cases"] >= 8
    assert result["wrong_auto_match_rate"] == 0
    assert result["match_precision"] == 1.0


def test_packaged_and_editable_benchmark_datasets_are_in_sync():
    from bibverify.benchmark import default_dataset

    packaged = json.loads(default_dataset().read_text(encoding="utf-8"))
    editable = json.loads((ROOT / "benchmarks" / "cases.json").read_text(encoding="utf-8"))
    assert packaged == editable


def test_benchmark_cli_emits_machine_readable_metrics():
    result = CliRunner().invoke(
        app, ["benchmark", "--dataset", str(ROOT / "benchmarks" / "cases.json")]
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["wrong_auto_match_rate"] == 0


def test_benchmark_cli_uses_packaged_dataset_by_default():
    result = CliRunner().invoke(app, ["benchmark"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["cases"] >= 8
