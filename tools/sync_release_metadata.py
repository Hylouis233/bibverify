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
        if package.get("registryType") in {"pypi", "npm"}:
            package["version"] = version
        if package.get("registryType") == "oci":
            package["identifier"] = f"ghcr.io/hylouis233/bibverify:{version}"
    return server


def expected_npm_package() -> dict:
    path = ROOT / "npm" / "package.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    package["version"] = source_version()
    return package


def expected_npm_lock() -> dict:
    path = ROOT / "npm" / "package-lock.json"
    lock = json.loads(path.read_text(encoding="utf-8"))
    version = source_version()
    lock["version"] = version
    lock["packages"][""]["version"] = version
    return lock


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated metadata is stale.")
    args = parser.parse_args()
    generated = {
        ROOT / "server.json": expected_server(),
        ROOT / "npm" / "package.json": expected_npm_package(),
        ROOT / "npm" / "package-lock.json": expected_npm_lock(),
    }
    if args.check:
        stale = [
            str(path.relative_to(ROOT))
            for path, payload in generated.items()
            if path.read_text(encoding="utf-8")
            != json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        ]
        if stale:
            raise SystemExit(
                f"Generated metadata is stale ({', '.join(stale)}); "
                "run tools/sync_release_metadata.py"
            )
        return 0
    for path, payload in generated.items():
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
