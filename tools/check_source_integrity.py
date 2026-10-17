"""Fail when a tracked source file becomes a placeholder or shrinks by more than 80%.

Usage: python tools/check_source_integrity.py [BASE] [HEAD]
BASE defaults to HEAD~1, HEAD defaults to HEAD. Every source file that is modified,
renamed, or added between BASE and HEAD is compared. Deleted files are ignored.
An intentional large shrink can be allowed with a commit message trailer in the range:
    Source-Integrity-Allow: path/to/file.py
"""

from __future__ import annotations

import re
import subprocess
import sys

SOURCE_SUFFIXES = (".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh", ".ps1")
PLACEHOLDER = re.compile(r"^(placeholder[\w-]*|todo|tbd|fixme|\.\.\.)$", re.IGNORECASE)
MAX_SHRINK = 0.80
MIN_OLD_BYTES = 200
ALLOW_TRAILER = re.compile(r"^Source-Integrity-Allow:\s*(\S+)\s*$", re.MULTILINE)
NULL_SHA = "0" * 40


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def blob_size(rev: str, path: str) -> int:
    return int(git("cat-file", "-s", f"{rev}:{path}").strip())


def check(base: str, head: str) -> list[str]:
    allowed = set(ALLOW_TRAILER.findall(git("log", "--format=%B", f"{base}..{head}")))
    errors = []
    diff = git("diff", "--name-status", "-M", base, head)
    for line in diff.splitlines():
        parts = line.split("\t")
        status, new_path = parts[0], parts[-1]
        old_path = parts[1]
        if status.startswith("D") or not new_path.endswith(SOURCE_SUFFIXES):
            continue
        content = git("show", f"{head}:{new_path}")
        if PLACEHOLDER.fullmatch(content.strip()):
            errors.append(f"{new_path}: whole file content is the placeholder {content.strip()!r}")
            continue
        if status.startswith("A") or new_path in allowed:
            continue
        old, new = blob_size(base, old_path), blob_size(head, new_path)
        if old >= MIN_OLD_BYTES and new < old * (1 - MAX_SHRINK):
            errors.append(
                f"{new_path}: shrank from {old} to {new} bytes ({1 - new / old:.0%} smaller)"
            )
    return errors


def main(argv: list[str]) -> int:
    base = argv[0] if argv and argv[0] not in ("", NULL_SHA) else "HEAD~1"
    head = argv[1] if len(argv) > 1 else "HEAD"
    errors = check(base, head)
    if errors:
        print(f"Source integrity check failed for {base}..{head}:")
        for error in errors:
            print(f"- {error}")
        print(
            "Fix: restore the real file content (for example `git checkout "
            f"{base} -- <path>`). If the shrink is intentional, add the commit trailer "
            "`Source-Integrity-Allow: <path>`."
        )
        return 1
    print(f"Source integrity check passed for {base}..{head}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
