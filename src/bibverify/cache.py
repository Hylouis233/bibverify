"""Small cross-process SQLite cache for successful idempotent GET responses."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Any


class ResponseCache:
    def __init__(self, path: str | Path, *, ttl_seconds: float = 604800) -> None:
        self.path = Path(path).expanduser().resolve(strict=False)
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            "cache_key TEXT PRIMARY KEY, created REAL NOT NULL, status INTEGER NOT NULL, "
            "headers TEXT NOT NULL, body BLOB NOT NULL)"
        )
        return connection

    @staticmethod
    def make_key(url: str, kwargs: dict[str, Any]) -> str:
        params = kwargs.get("params") or {}
        headers = {
            str(key).lower(): str(value)
            for key, value in (kwargs.get("headers") or {}).items()
            if str(key).lower() not in {"authorization", "x-api-key", "cookie"}
        }
        payload = json.dumps(
            {"url": url, "params": params, "headers": headers},
            ensure_ascii=True,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> tuple[int, dict[str, str], bytes] | None:
        if self.ttl_seconds == 0 or not self.path.exists():
            return None
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT created, status, headers, body FROM responses WHERE cache_key = ?", (key,)
            ).fetchone()
            if row is None:
                return None
            created, status, headers, body = row
            if time.time() - float(created) > self.ttl_seconds:
                connection.execute("DELETE FROM responses WHERE cache_key = ?", (key,))
                connection.commit()
                return None
            return int(status), json.loads(headers), bytes(body)

    def put(self, key: str, status: int, headers: dict[str, str], body: bytes) -> None:
        # Cache only successful, bounded responses. Failures must be retried so
        # temporary rate limits and outages cannot poison future verification.
        if not 200 <= status < 300 or len(body) > 10 * 1024 * 1024:
            return
        safe_headers = {
            key: value
            for key, value in headers.items()
            if key.lower() in {"content-type", "etag", "last-modified"}
        }
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO responses(cache_key, created, status, headers, body) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, time.time(), status, json.dumps(safe_headers), body),
            )
            connection.commit()

    def clear(self) -> bool:
        removed = False
        for path in (
            self.path,
            self.path.with_name(self.path.name + "-wal"),
            self.path.with_name(self.path.name + "-shm"),
        ):
            if path.exists():
                path.unlink()
                removed = True
        return removed
