"""Regression coverage for the unresolved DOI review findings in PR #32."""

from unittest.mock import patch

import pytest
from mcp import Client
from typer.testing import CliRunner

from bibverify.checker import BibTeXChecker
from bibverify.cli import app
from bibverify.i18n import LanguageSupport
from bibverify.mcp_server import create_server, handle_request
from bibverify.models import ProviderResult, QueryStatus


@pytest.fixture(params=["CN", "EN"])
def checker(tmp_path, request):
    service = BibTeXChecker(
        tmp_path / "missing.json",
        overrides={
            "query_settings": {"delay_between_requests": 0},
            "user_info": {"email": "fixture@example.test"},
        },
    )
    service.lang = LanguageSupport(request.param)
    return service


def compat_call(doi):
    return handle_request(
        {
            "jsonrpc": "2.0",
            "id": 19,
            "method": "tools/call",
            "params": {"name": "doi_to_bibtex", "arguments": {"doi": doi}},
        }
    )


@pytest.mark.parametrize("doi", ["", "   ", "\t\n"])
def test_empty_doi_keeps_invalid_input_without_network(checker, requests_mock, doi):
    bibtex, result = checker.bibtex_from_doi_result(doi)

    assert bibtex is None
    assert result.status is QueryStatus.INVALID_INPUT
    assert requests_mock.call_count == 0
    message = checker.doi_lookup_failure_message(doi, result)
    assert message == checker.lang.get_text("doi_invalid_input")
    assert message != "doi_invalid_input"
    assert message != checker.lang.get_text("doi_not_found", doi=doi)


@pytest.mark.parametrize("doi", ["", "   ", "\t\n"])
def test_empty_doi_cli_and_compat_are_input_errors(checker, requests_mock, doi):
    with patch("bibverify.cli.BibTeXChecker", return_value=checker):
        cli = CliRunner().invoke(app, ["doi", doi])
    with patch("bibverify.mcp_server.BibTeXChecker", return_value=checker):
        compat = compat_call(doi)

    expected = checker.lang.get_text("doi_invalid_input")
    assert cli.exit_code == 5
    assert expected in cli.stderr
    assert compat["result"]["isError"] is True
    assert expected in compat["result"]["content"][0]["text"]
    assert requests_mock.call_count == 0


@pytest.mark.anyio
@pytest.mark.parametrize("doi", ["", "   ", "\t\n"])
async def test_official_mcp_preserves_invalid_doi_message(checker, requests_mock, doi):
    with patch("bibverify.mcp_server.BibTeXChecker", return_value=checker):
        server = create_server("__missing_test_config__.json")
        async with Client(server) as client:
            response = await client.call_tool("doi_to_bibtex", {"doi": doi})

    assert response.is_error
    assert checker.lang.get_text("doi_invalid_input") in response.content[0].text
    assert requests_mock.call_count == 0


def test_crossref_rate_limit_has_supported_localized_remedy(checker):
    result = ProviderResult(
        "crossref",
        QueryStatus.RATE_LIMITED,
        http_status=429,
        error="private-provider-detail https://private.invalid/?token=example",
    )
    message = checker.doi_lookup_failure_message("10.1000/limited", result)

    assert message == checker.lang.get_text("crossref_rate_limit_429")
    assert message != "crossref_rate_limit_429"
    assert "Crossref" in message
    assert "user_info.email" in message
    assert "API key" not in message
    assert "private-provider-detail" not in message
    assert "https://" not in message
    assert "稍后" in message or "retry" in message.lower()


@pytest.mark.anyio
async def test_official_mcp_rate_limit_uses_actual_localized_remedy(checker):
    result = ProviderResult("crossref", QueryStatus.RATE_LIMITED, http_status=429)
    with (
        patch.object(checker.provider_registry["crossref"], "lookup", return_value=result),
        patch("bibverify.mcp_server.BibTeXChecker", return_value=checker),
    ):
        server = create_server("__missing_test_config__.json")
        async with Client(server) as client:
            response = await client.call_tool("doi_to_bibtex", {"doi": "10.1000/limited"})

    assert response.is_error
    assert checker.lang.get_text("crossref_rate_limit_429") in response.content[0].text
    assert "API key" not in response.content[0].text


@pytest.mark.parametrize(
    ("status", "exit_code", "message_key"),
    [
        (QueryStatus.NO_MATCH, 1, "doi_not_found"),
        (QueryStatus.IDENTIFIER_CONFLICT, 3, "doi_identifier_conflict"),
        (QueryStatus.RATE_LIMITED, 4, "crossref_rate_limit_429"),
    ],
)
def test_other_doi_statuses_keep_transport_boundaries(checker, status, exit_code, message_key):
    result = ProviderResult("crossref", status)
    doi = "10.1000/example"
    with patch.object(checker.provider_registry["crossref"], "lookup", return_value=result):
        with patch("bibverify.cli.BibTeXChecker", return_value=checker):
            cli = CliRunner().invoke(app, ["doi", doi])
        with patch("bibverify.mcp_server.BibTeXChecker", return_value=checker):
            compat = compat_call(doi)

    expected = checker.lang.get_text(message_key, doi=doi)
    assert cli.exit_code == exit_code
    assert compat["result"]["isError"] is True
    assert expected in compat["result"]["content"][0]["text"]
    if status is QueryStatus.RATE_LIMITED:
        assert "API key" not in cli.stderr
        assert "user_info.email" in cli.stderr
