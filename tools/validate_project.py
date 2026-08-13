"""Validate repository metadata, workflows, documentation links, and action pins."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ACTION_PIN = re.compile(r"^\s*-?\s*uses:\s*[^\s@]+@([0-9a-f]{40})(?:\s+#.*)?$", re.MULTILINE)
ACTION_USE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def validate_json() -> None:
    paths = [ROOT / "server.json", ROOT / "config_template.json"]
    paths.extend((ROOT / "benchmarks").glob("*.json"))
    paths.extend((ROOT / "tests" / "fixtures").rglob("*.json"))
    paths.extend((ROOT / "src" / "bibverify" / "data").glob("*.json"))
    for path in paths:
        json.loads(path.read_text(encoding="utf-8"))


def validate_toml() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        tomllib.load(stream)


def validate_yaml() -> None:
    paths = [ROOT / ".github" / "dependabot.yml"]
    paths.extend((ROOT / ".github" / "workflows").glob("*.yml"))
    for path in paths:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError(f"YAML document root must be a mapping: {path}")


def validate_action_pins() -> None:
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        uses = ACTION_USE.findall(text)
        pins = ACTION_PIN.findall(text)
        if len(uses) != len(pins):
            unpinned = [value for value in uses if not re.search(r"@[0-9a-f]{40}$", value)]
            raise ValueError(f"Unpinned GitHub Actions in {path.name}: {unpinned}")


def validate_markdown_links() -> None:
    for path in (ROOT / "README.md", ROOT / "README_EN.md"):
        for target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8")):
            target = target.strip().split("#", 1)[0]
            if not target or "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target).resolve(strict=False)
            if not resolved.exists():
                raise FileNotFoundError(f"Broken local link in {path.name}: {target}")


def main() -> int:
    validate_json()
    validate_toml()
    validate_yaml()
    validate_action_pins()
    validate_markdown_links()
    print("Project metadata validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
