import json
import re
import unittest
from pathlib import Path

import bibverify


ROOT = Path(__file__).resolve().parents[1]


class PublishMetadataTests(unittest.TestCase):
    def test_mcp_registry_metadata_matches_package(self):
        server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))

        self.assertEqual(server["name"], "io.github.hylouis233/bibverify")
        self.assertEqual(server["version"], bibverify.__version__)
        self.assertEqual(server["packages"][0]["registryType"], "pypi")
        self.assertEqual(server["packages"][0]["identifier"], "bibverify")
        self.assertEqual(server["packages"][0]["version"], bibverify.__version__)
        self.assertEqual(server["packages"][0]["packageArguments"][0]["value"], "mcp")

    def test_readme_contains_mcp_registry_ownership_marker(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("mcp-name: io.github.hylouis233/bibverify", readme)

    def test_project_version_matches_package_version(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), bibverify.__version__)

    def test_clawhub_skill_has_required_frontmatter(self):
        skill = (ROOT / "clawhub" / "bibverify" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("name: bibverify", skill)
        self.assertIn("description:", skill)
        self.assertIn("verify_bib_file", skill)


if __name__ == "__main__":
    unittest.main()
