import io
import json
import tempfile
import unittest
from pathlib import Path

from bibverify.agent import build_mcp_config, build_skill_markdown, doctor, init_agent
from bibverify.mcp_server import handle_request, run_stdio_server


class AgentIntegrationTests(unittest.TestCase):
    def test_skill_mentions_mcp_tools(self):
        content = build_skill_markdown(target="codex", config_file="custom.json")

        self.assertIn("doi_to_bibtex", content)
        self.assertIn("verify_bib_file", content)
        self.assertIn("custom.json", content)

    def test_mcp_config_uses_bibverify_mcp_command(self):
        config = build_mcp_config(config_file="custom.json")

        self.assertEqual(config["mcpServers"]["bibverify"]["command"], "bibverify")
        self.assertEqual(config["mcpServers"]["bibverify"]["args"], ["mcp", "--config", "custom.json"])

    def test_agent_init_writes_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = init_agent(target="generic", output=tmp, config_file="custom.json")
            names = {Path(path).name for path in paths}

            self.assertEqual(names, {"SKILL.md", "mcp.json", "README.md"})
            self.assertTrue((Path(tmp) / "SKILL.md").exists())
            mcp = json.loads((Path(tmp) / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(mcp["mcpServers"]["bibverify"]["args"], ["mcp", "--config", "custom.json"])

    def test_doctor_reports_missing_config_as_warning(self):
        checks = doctor(config_file="__missing_test_config__.json")
        config_check = [check for check in checks if check["name"] == "config"][0]

        self.assertFalse(config_check["ok"])

    def test_mcp_initialize_and_tools_list(self):
        initialize = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        tools = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        self.assertEqual(initialize["result"]["serverInfo"]["name"], "bibverify")
        self.assertTrue(any(tool["name"] == "doi_to_bibtex" for tool in tools["result"]["tools"]))

    def test_mcp_stdio_emits_json_lines(self):
        stdin = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n")
        stdout = io.StringIO()

        run_stdio_server(stdin=stdin, stdout=stdout)

        response = json.loads(stdout.getvalue())
        self.assertEqual(response["id"], 1)
        self.assertIn("tools", response["result"])


if __name__ == "__main__":
    unittest.main()
