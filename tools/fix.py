"""Apply the formatter fixes CI would ask for, then run CI's exact lint and format checks.

Usage: python tools/fix.py [--check]

Run this before every push. It derives the ruff paths from the `quality` job in
.github/workflows/ci.yml, so it always formats exactly what CI checks. Only
semantics-preserving fixes are applied automatically (ruff format and import sorting);
any other lint finding is printed and the exit code is non-zero, because those need a
human decision (for example re-exports that look unused).
With --check nothing is modified; only CI's two commands are run.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
LINT_PREFIX = ["python", "-m", "ruff", "check"]
FORMAT_PREFIX = ["python", "-m", "ruff", "format", "--check"]


def ci_ruff_commands(workflow_text: str) -> tuple[list[str], list[str]]:
    """Return CI's `ruff check` and `ruff format --check` commands from the quality job."""
    steps = yaml.safe_load(workflow_text)["jobs"]["quality"]["steps"]
    runs = [shlex.split(str(step["run"])) for step in steps if "run" in step]
    lint = [cmd for cmd in runs if cmd[:4] == LINT_PREFIX]
    fmt = [cmd for cmd in runs if cmd[:5] == FORMAT_PREFIX]
    if len(lint) != 1 or len(fmt) != 1:
        raise SystemExit(
            "tools/fix.py: expected exactly one `python -m ruff check` and one "
            "`python -m ruff format --check` step in the quality job of "
            ".github/workflows/ci.yml; update tools/fix.py together with the workflow."
        )
    return lint[0], fmt[0]


def run(cmd: list[str]) -> int:
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run([sys.executable, *cmd[1:]], cwd=ROOT).returncode


def main(argv: list[str]) -> int:
    lint, fmt = ci_ruff_commands(WORKFLOW.read_text(encoding="utf-8"))
    paths = fmt[5:]
    if "--check" not in argv:
        run([*LINT_PREFIX, "--fix", "--select", "I", *paths])
        run(["python", "-m", "ruff", "format", *paths])
    lint_status, fmt_status = run(lint), run(fmt)
    if lint_status or fmt_status:
        hint = (
            "run `python tools/fix.py` to apply the formatter fixes."
            if "--check" in argv
            else "they were not auto-fixed because they need a code decision."
        )
        print(
            f"tools/fix.py: CI's quality job would reject the findings above; {hint}",
            file=sys.stderr,
        )
        return 1
    print("tools/fix.py: ruff check and ruff format --check pass with CI's exact commands.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
