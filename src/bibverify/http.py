"""Shared resilient HTTP client used by every metadata provider."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bibverify.cache import ResponseCache


class ResilientSession:
    """Connection-pooled requests session with retries and per-host pacing."""

    def __init__(
        self,
        *,
        timeout: float | tuple[float, float] = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        min_interval: float = 0.0,
        user_agent: str = "Bibverify/0.3",
        sleep: Callable[[float], None] = time.sleep,
        session: requests.Session | None = None,
        cache: ResponseCache | None = None,
    ) -> None:
        self.timeout = timeout
        self.min_interval = min_interval
        self._sleep = sleep
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()
        self.session = session or requests.Session()
        self.cache = cache
        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            status_forcelist=(408, 429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
            backoff_factor=backoff_factor,
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.setdefault("User-Agent", user_agent)

    def _pace(self, url: str) -> None:
        if self.min_interval <= 0:
            return
        host = urlparse(url).netloc.lower()
        with self._lock:
            now = time.monotonic()
            wait_for = self.min_interval - (now - self._last_request.get(host, 0.0))
            if wait_for > 0:
                self._sleep(wait_for)
            self._last_request[host] = time.monotonic()

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a paced GET using the configured default timeout."""
        cache_key = self.cache.make_key(url, kwargs) if self.cache else None
        cached = self.cache.get(cache_key) if self.cache and cache_key else None
        if cached is not None:
            status, headers, body = cached
            response = requests.Response()
            response.status_code = status
            response.headers.update(headers)
            response._content = body
            response.url = url
            response.encoding = requests.utils.get_encoding_from_headers(response.headers)
            response.from_cache = True  # type: ignore[attr-defined]
            return response
        self._pace(url)
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.get(url, **kwargs)
        if self.cache and cache_key:
            self.cache.put(
                cache_key, response.status_code, dict(response.headers), response.content
            )
        return response

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> ResilientSession:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
