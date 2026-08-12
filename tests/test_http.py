from unittest.mock import Mock

from bibverify.http import ResilientSession


def test_http_client_applies_default_timeout_and_user_agent():
    session = Mock()
    session.headers = {}
    session.mount = Mock()
    response = Mock()
    session.get.return_value = response
    client = ResilientSession(
        timeout=7.5,
        max_retries=2,
        user_agent="Bibverify/Test",
        session=session,
    )

    assert client.get("https://example.test/work", params={"q": "x"}) is response
    session.get.assert_called_once_with(
        "https://example.test/work",
        params={"q": "x"},
        timeout=7.5,
    )
    assert session.headers["User-Agent"] == "Bibverify/Test"
    assert session.mount.call_count == 2


def test_http_client_configures_retryable_statuses():
    session = Mock()
    session.headers = {}
    mounted = []
    session.mount.side_effect = lambda prefix, adapter: mounted.append((prefix, adapter))

    ResilientSession(max_retries=4, backoff_factor=1.25, session=session)

    retry = mounted[0][1].max_retries
    assert retry.total == 4
    assert retry.backoff_factor == 1.25
    assert 429 in retry.status_forcelist
    assert 503 in retry.status_forcelist
    assert retry.respect_retry_after_header is True
