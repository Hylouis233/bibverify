"""Smoke-test and package a native Bibverify executable for release."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    package_version = version("bibverify")
    binary = root / "dist-standalone" / ("bibverify.exe" if os.name == "nt" else "bibverify")
    if not binary.is_file():
        raise FileNotFoundError(binary)

    completed = subprocess.run(
        [str(binary), "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.stdout.strip() != package_version:
        raise RuntimeError(f"Unexpected standalone version: {completed.stdout!r}")

    runner_os = os.getenv("RUNNER_OS", sys.platform).lower().replace("darwin", "macos")
    runner_arch = os.getenv(
        "RUNNER_ARCH", os.environ.get("PROCESSOR_ARCHITECTURE", "unknown")
    ).lower()
    release_dir = root / "release"
    release_dir.mkdir(exist_ok=True)
    archive_base = release_dir / f"bibverify-{package_version}-{runner_os}-{runner_arch}"

    staging = root / "build" / "standalone-package"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copy2(binary, staging / binary.name)
    shutil.copy2(root / "LICENSE", staging / "LICENSE")
    shutil.copy2(root / "README_EN.md", staging / "README.md")

    archive = shutil.make_archive(str(archive_base), "zip" if os.name == "nt" else "gztar", staging)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
