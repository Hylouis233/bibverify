from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bibverify_fix_tool", ROOT / "tools" / "fix.py")
assert _spec and _spec.loader
fix_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fix_tool)

# Lines from src/bibverify/matching.py before and after commit 9898801
# ("style: ruff-format page_score comparison in matching"), a real follow-up format commit.
BEFORE = (
    "def score(original, candidate, normalize_pages, weighted):\n"
    '    if original.get("pages") and candidate.get("pages"):\n'
    '        page_score = float(normalize_pages(original["pages"]) == normalize_pages(candidate["pages"]))\n'
    "        weighted.append((page_score, 0.05))\n"
)
AFTER = (
    "def score(original, candidate, normalize_pages, weighted):\n"
    '    if original.get("pages") and candidate.get("pages"):\n'
    "        page_score = float(\n"
    '            normalize_pages(original["pages"]) == normalize_pages(candidate["pages"])\n'
    "        )\n"
    "        weighted.append((page_score, 0.05))\n"
)


def test_paths_come_from_ci_quality_job() -> None:
    lint, fmt = fix_tool.ci_ruff_commands(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    assert lint[4:] == fmt[5:]
    assert "src" in fmt and "tests" in fmt


def test_missing_ci_step_fails_closed() -> None:
    workflow = "jobs:\n  quality:\n    steps:\n      - run: python -m pytest\n"
    with pytest.raises(SystemExit, match="expected exactly one"):
        fix_tool.ci_ruff_commands(workflow)


def test_past_style_commit_is_reproduced_by_ruff_format(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text(BEFORE, encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--config",
            str(ROOT / "pyproject.toml"),
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    assert target.read_text(encoding="utf-8") == AFTER
