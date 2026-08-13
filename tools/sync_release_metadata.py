"""Synchronize generated release metadata from the package version source."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_version() -> str:
    text = (ROOT / "src" / "bibverify" / "_version.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', text, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("Could not read __version__ from src/bibverify/_version.py")
    return match.group(1)


def expected_server() -> dict:
    server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    version = source_version()
    server["version"] = version
    for package in server.get("packages", []):
        if package.get("registryType") == "pypi":
            package["version"] = version
    return server


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated metadata is stale.")
    args = parser.parse_args()
    path = ROOT / "server.json"
    expected = json.dumps(expected_server(), ensure_ascii=False, indent=2) + "\n"
    current = path.read_text(encoding="utf-8")
    if args.check:
        if current != expected:
            raise SystemExit("server.json is stale; run tools/sync_release_metadata.py")
        return 0
    path.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
