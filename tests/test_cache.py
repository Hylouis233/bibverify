from __future__ import annotations

import json
from unittest.mock import Mock

from typer.testing import CliRunner

from bibverify.cache import ResponseCache
from bibverify.cli import app
from bibverify.http import ResilientSession


def test_http_cache_avoids_duplicate_successful_requests(tmp_path):
    session = Mock()
    session.headers = {}
    session.mount = Mock()
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.content = b'{"ok": true}'
    session.get.return_value = response
    cache = ResponseCache(tmp_path / "responses.sqlite3", ttl_seconds=60)
    client = ResilientSession(session=session, cache=cache)

    assert client.get("https://example.test/data", params={"q": "x"}) is response
    cached = client.get("https://example.test/data", params={"q": "x"})

    assert session.get.call_count == 1
    assert cached.json() == {"ok": True}
    assert cached.from_cache is True


def test_http_cache_does_not_store_failures(tmp_path):
    session = Mock()
    session.headers = {}
    session.mount = Mock()
    response = Mock()
    response.status_code = 503
    response.headers = {}
    response.content = b"unavailable"
    session.get.return_value = response
    client = ResilientSession(
        session=session, cache=ResponseCache(tmp_path / "responses.sqlite3", ttl_seconds=60)
    )

    client.get("https://example.test/data")
    client.get("https://example.test/data")

    assert session.get.call_count == 2


def test_cache_clear_command_removes_configured_cache(tmp_path):
    cache_path = tmp_path / "state" / "cache.sqlite3"
    cache = ResponseCache(cache_path)
    cache.put("key", 200, {"Content-Type": "application/json"}, b"{}")
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps({"query_settings": {"cache_path": str(cache_path)}}), encoding="utf-8"
    )

    result = CliRunner().invoke(app, ["cache", "clear", "--config", str(config)])

    assert result.exit_code == 0
    assert not cache_path.exists()
