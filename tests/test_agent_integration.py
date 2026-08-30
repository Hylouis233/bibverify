import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import anyio
import pytest
from mcp import Client
from mcp_types import LATEST_PROTOCOL_VERSION

from bibverify.agent import build_mcp_config, build_skill_markdown, doctor, init_agent
from bibverify.mcp_server import create_server, handle_request, run_stdio_server
from bibverify.models import ProviderResult, QueryStatus


class AgentIntegrationTests(unittest.TestCase):
    def test_skill_mentions_mcp_tools(self):
        content = build_skill_markdown(target="codex", config_file="custom.json")

        self.assertIn("doi_to_bibtex", content)
        self.assertIn("verify_bib_file", content)
        self.assertIn("custom.json", content)

    def test_mcp_config_uses_bibverify_mcp_command(self):
        config = build_mcp_config(config_file="custom.json")

        self.assertEqual(config["mcpServers"]["bibverify"]["command"], "bibverify")
        self.assertEqual(
            config["mcpServers"]["bibverify"]["args"], ["mcp", "--config", "custom.json"]
        )

    def test_agent_init_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = init_agent(target="generic", output=tmp, config_file="custom.json")
            names = {Path(path).name for path in paths}

            self.assertEqual(names, {"SKILL.md", "mcp.json", "README.md"})
            self.assertTrue((Path(tmp) / "SKILL.md").exists())
            mcp = json.loads((Path(tmp) / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                mcp["mcpServers"]["bibverify"]["args"], ["mcp", "--config", "custom.json"]
            )

    def test_doctor_reports_missing_config_as_warning(self):
        checks = doctor(config_file="__missing_test_config__.json")
        config_check = next(check for check in checks if check["name"] == "config")

        self.assertFalse(config_check["ok"])

    def test_mcp_initialize_and_tools_list(self):
        initialize = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        tools = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        self.assertEqual(initialize["result"]["serverInfo"]["name"], "bibverify")
        self.assertEqual(initialize["result"]["protocolVersion"], LATEST_PROTOCOL_VERSION)
        self.assertTrue(any(tool["name"] == "doi_to_bibtex" for tool in tools["result"]["tools"]))

    def test_mcp_stdio_emits_json_lines(self):
        stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n")
        stdout = io.StringIO()

        run_stdio_server(stdin=stdin, stdout=stdout)

        response = json.loads(stdout.getvalue())
        self.assertEqual(response["id"], 1)
        self.assertIn("tools", response["result"])

    def test_verify_bib_file_returns_structured_summary(self):
        with patch("bibverify.mcp_server.BibTeXChecker") as checker_class:
            checker = checker_class.return_value
            checker.run.return_value = {
                "bib_file": "references.bib",
                "counts": {"total": 1, "verified": 1, "updated": 0, "not_found": 0, "errors": 0},
                "files": {
                    "report": "bib_check_report_fixed.txt",
                    "backup": "references_backup_fixed.bib",
                    "updated": None,
                    "wrong": None,
                },
            }

            response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "verify_bib_file",
                        "arguments": {"config_file": "config.json"},
                    },
                }
            )

        structured = response["result"]["structuredContent"]
        self.assertEqual(structured["counts"]["total"], 1)
        self.assertEqual(structured["files"]["backup"], "references_backup_fixed.bib")


@pytest.mark.anyio
async def test_official_mcp_sdk_lists_and_calls_tools():
    with redirect_stdout(io.StringIO()):
        server = create_server("__missing_test_config__.json")

    async with Client(server) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        result = await client.call_tool(
            "explain_update_diff",
            {
                "original": {"title": "Old title"},
                "updated": {"title": "New title"},
            },
        )

    assert {
        "doi_to_bibtex",
        "rank_lookup_sources",
        "explain_update_diff",
        "verify_bib_file",
    } <= names
    assert result.structured_content["differences"]["title"]["original"] == "Old title"


@pytest.mark.anyio
async def test_mcp_preserves_expected_doi_not_found_error():
    with patch("bibverify.mcp_server.BibTeXChecker") as checker_class:
        checker = checker_class.return_value
        checker.bibtex_from_doi_result.return_value = (
            None,
            ProviderResult("crossref", QueryStatus.NO_MATCH),
        )
        checker.doi_lookup_failure_message.return_value = (
            "Could not find a reference for DOI: 10.0/missing"
        )
        server = create_server("__missing_test_config__.json")

        async with Client(server) as client:
            result = await client.call_tool("doi_to_bibtex", {"doi": "10.0/missing"})

    assert result.is_error
    assert "Could not find a reference for DOI" in result.content[0].text


@pytest.mark.anyio
async def test_mcp_does_not_report_crossref_rate_limit_as_doi_not_found():
    with patch("bibverify.mcp_server.BibTeXChecker") as checker_class:
        checker = checker_class.return_value
        checker.bibtex_from_doi_result.return_value = (
            None,
            ProviderResult("crossref", QueryStatus.RATE_LIMITED, http_status=429),
        )
        checker.doi_lookup_failure_message.return_value = (
            "Crossref rate limit - recommend adding API key"
        )
        server = create_server("__missing_test_config__.json")

        async with Client(server) as client:
            result = await client.call_tool("doi_to_bibtex", {"doi": "10.0/rate-limited"})

    assert result.is_error
    assert "rate limit" in result.content[0].text
    assert "not find" not in result.content[0].text


def test_compat_mcp_preserves_crossref_rate_limit_status():
    with patch("bibverify.mcp_server.BibTeXChecker") as checker_class:
        checker = checker_class.return_value
        checker.bibtex_from_doi_result.return_value = (
            None,
            ProviderResult("crossref", QueryStatus.RATE_LIMITED, http_status=429),
        )
        checker.doi_lookup_failure_message.return_value = (
            "Crossref rate limit - recommend adding API key"
        )
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "doi_to_bibtex",
                    "arguments": {"doi": "10.0/rate-limited"},
                },
            }
        )

    text = response["result"]["content"][0]["text"]
    assert response["result"]["isError"] is True
    assert "rate limit" in text
    assert "not find" not in text


@pytest.mark.anyio
async def test_mcp_and_compat_reject_crossref_identifier_conflict():
    with patch("bibverify.mcp_server.BibTeXChecker") as checker_class:
        checker = checker_class.return_value
        checker.bibtex_from_doi_result.return_value = (
            None,
            ProviderResult("crossref", QueryStatus.IDENTIFIER_CONFLICT),
        )
        checker.doi_lookup_failure_message.return_value = "Crossref DOI conflict"
        server = create_server("__missing_test_config__.json")

        async with Client(server) as client:
            official = await client.call_tool("doi_to_bibtex", {"doi": "10.0/conflict"})

        compat = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "doi_to_bibtex",
                    "arguments": {"doi": "10.0/conflict"},
                },
            }
        )

    assert official.is_error
    assert "conflict" in official.content[0].text
    assert compat["result"]["isError"] is True
    assert "conflict" in compat["result"]["content"][0]["text"]


def test_mcp_rejects_config_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    server = create_server(workspace / "config.json", workspace_root=workspace)

    async def call():
        async with Client(server) as client:
            return await client.call_tool(
                "rank_lookup_sources",
                {"title": "A title", "config_file": str(outside)},
            )

    result = anyio.run(call)
    assert result.is_error
    assert "workspace root" in result.content[0].text
    assert str(workspace) not in result.content[0].text


def test_mcp_rejects_config_that_points_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = workspace / "config.json"
    config.write_text(json.dumps({"bib_file": str(tmp_path / "outside.bib")}), encoding="utf-8")
    server = create_server(config, workspace_root=workspace)

    async def call():
        async with Client(server) as client:
            return await client.call_tool("rank_lookup_sources", {"title": "A title"})

    result = anyio.run(call)
    assert result.is_error
    assert "bib_file must stay" in result.content[0].text
    assert str(workspace) not in result.content[0].text


if __name__ == "__main__":
    unittest.main()
