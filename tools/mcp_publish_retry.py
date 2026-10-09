"""Recognize only known package-version propagation failures from mcp-publisher."""

from __future__ import annotations

import json
import re
import sys

PREFIX = "Error: publish failed: server returned status 400: "
BANNER = "Publishing to https://registry.modelcontextprotocol.io..."
MESSAGE = re.compile(
    r"registry validation failed for package [0-9]+ \((?P<package>[^\s()']+)\): "
    r"(?P<registry>PyPI|NPM) package '(?P=package)' exists, but version "
    r"'(?P<version>[^\s']+)' was not found \(status: 404\)\. "
    r"A newly published release can take a moment to appear on "
    r"(?P<destination>PyPI|the registry)\. Wait and retry, or publish version "
    r"'(?P=version)' before registering it"
)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON fields rather than silently discarding evidence."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def is_propagation_failure(output: str) -> bool:
    """Fail closed unless the complete output is a recognized 400 response."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if lines and lines[0] == BANNER:
        lines.pop(0)
    if len(lines) != 1 or not lines[0].startswith(PREFIX):
        return False
    try:
        payload = json.loads(lines[0][len(PREFIX) :], object_pairs_hook=unique_object)
    except (ValueError, RecursionError):
        return False
    if not isinstance(payload, dict) or set(payload) != {"title", "status", "detail", "errors"}:
        return False
    if (
        payload["title"] != "Bad Request"
        or type(payload["status"]) is not int
        or payload["status"] != 400
        or payload["detail"] != "Failed to publish server"
    ):
        return False
    errors = payload["errors"]
    if not isinstance(errors, list) or not errors:
        return False
    for error in errors:
        if not isinstance(error, dict) or set(error) != {"message"}:
            return False
        message = error["message"]
        if not isinstance(message, str):
            return False
        match = MESSAGE.fullmatch(message)
        if match is None:
            return False
        expected = "PyPI" if match["registry"] == "PyPI" else "the registry"
        if match["destination"] != expected:
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(0 if is_propagation_failure(sys.stdin.read()) else 1)
