"""Smoke-test and package a native Bibverify executable for release."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


def normalized_target() -> tuple[str, str]:
    runner_os = os.getenv("RUNNER_OS", sys.platform).lower()
    operating_system = {
        "windows": "windows",
        "win32": "windows",
        "macos": "macos",
        "darwin": "macos",
        "linux": "linux",
    }.get(runner_os)
    if operating_system is None:
        raise RuntimeError(f"Unsupported standalone operating system: {runner_os}")

    runner_arch = os.getenv(
        "RUNNER_ARCH", os.environ.get("PROCESSOR_ARCHITECTURE", "unknown")
    ).lower()
    architecture = {
        "x64": "x64",
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(runner_arch)
    if architecture is None:
        raise RuntimeError(f"Unsupported standalone architecture: {runner_arch}")
    return operating_system, architecture


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    package_version = version("bibverify")
    binary = root / "dist-standalone" / ("bibverify.exe" if os.name == "nt" else "bibverify")
    if not binary.is_file():
        raise FileNotFoundError(binary)

    completed = subprocess.run(
        [str(binary), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="", file=sys.stdout)
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"Standalone smoke test failed with exit code {completed.returncode}")
    if completed.stdout.strip() != package_version:
        raise RuntimeError(f"Unexpected standalone version: {completed.stdout!r}")

    runner_os, runner_arch = normalized_target()
    release_dir = root / "release"
    release_dir.mkdir(exist_ok=True)
    archive_base = release_dir / f"bibverify-{package_version}-{runner_os}-{runner_arch}"
    released_binary = Path(f"{archive_base}.exe") if os.name == "nt" else archive_base
    shutil.copy2(binary, released_binary)
    if os.name != "nt":
        released_binary.chmod(0o755)

    staging = root / "build" / "standalone-package"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copy2(binary, staging / binary.name)
    shutil.copy2(root / "LICENSE", staging / "LICENSE")
    shutil.copy2(root / "README.md", staging / "README.md")

    archive = shutil.make_archive(str(archive_base), "zip" if os.name == "nt" else "gztar", staging)
    print(released_binary)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
