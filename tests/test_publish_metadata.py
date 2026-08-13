import json
import re
import unittest
from pathlib import Path

import bibverify

ROOT = Path(__file__).resolve().parents[1]


class PublishMetadataTests(unittest.TestCase):
    def test_mcp_registry_metadata_matches_package(self):
        server = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))

        self.assertEqual(server["name"], "io.github.Hylouis233/bibverify")
        self.assertEqual(server["version"], bibverify.__version__)
        self.assertEqual(server["packages"][0]["registryType"], "pypi")
        self.assertEqual(server["packages"][0]["identifier"], "bibverify")
        self.assertEqual(server["packages"][0]["version"], bibverify.__version__)
        self.assertEqual(server["packages"][0]["packageArguments"][0]["value"], "mcp")
        self.assertEqual(server["packages"][1]["registryType"], "npm")
        self.assertEqual(server["packages"][1]["identifier"], "@hylouis233/bibverify")
        self.assertEqual(server["packages"][1]["version"], bibverify.__version__)
        self.assertEqual(server["packages"][2]["registryType"], "oci")
        self.assertEqual(
            server["packages"][2]["identifier"],
            f"ghcr.io/hylouis233/bibverify:{bibverify.__version__}",
        )

    def test_readme_contains_mcp_registry_ownership_marker(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("mcp-name: io.github.Hylouis233/bibverify", readme)
        self.assertIsNone(re.search(r"[\u3400-\u9fff]", readme))
        self.assertTrue((ROOT / "README_CN.md").is_file())

    def test_project_uses_package_version_as_dynamic_source(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('dynamic = ["version"]', pyproject)
        self.assertIn('version = {attr = "bibverify._version.__version__"}', pyproject)

    def test_generated_release_metadata_is_current(self):
        from tools.sync_release_metadata import (
            expected_npm_lock,
            expected_npm_package,
            expected_server,
        )

        actual = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected_server())
        npm_package = json.loads((ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(npm_package, expected_npm_package())
        npm_lock = json.loads((ROOT / "npm" / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(npm_lock, expected_npm_lock())

    def test_clawhub_skill_has_required_frontmatter(self):
        skill = (ROOT / "clawhub" / "bibverify" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("name: bibverify", skill)
        self.assertIn("description:", skill)
        self.assertIn("verify_bib_file", skill)

    def test_standalone_release_targets_the_repository_explicitly(self):
        workflow = (ROOT / ".github" / "workflows" / "publish-standalone.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("GH_REPO: ${{ github.repository }}", workflow)
        self.assertIn('--repo "${GH_REPO}"', workflow)
        self.assertIn("release_tag:", workflow)
        self.assertIn("ref: ${{ inputs.release_tag || github.ref }}", workflow)
        self.assertIn("RELEASE_TAG: ${{ inputs.release_tag || github.ref_name }}", workflow)

    def test_mcp_publish_retries_registry_dependency_propagation(self):
        workflow = (ROOT / ".github" / "workflows" / "publish-mcp.yml").read_text(encoding="utf-8")

        self.assertIn("for attempt in {1..60}", workflow)
        self.assertIn("sleep 30", workflow)


if __name__ == "__main__":
    unittest.main()
