from pathlib import Path

import yaml
from tools.validate_project import (
    validate_action_pins,
    validate_json,
    validate_markdown_links,
    validate_toml,
    validate_yaml,
)

ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_and_links_are_valid():
    validate_json()
    validate_toml()
    validate_yaml()
    validate_action_pins()
    validate_markdown_links()


def test_codeql_action_steps_stay_on_one_version():
    workflow = yaml.safe_load((ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8"))
    uses = [
        step["uses"]
        for step in workflow["jobs"]["analyze"]["steps"]
        if step.get("uses", "").startswith("github/codeql-action/")
    ]
    refs = {value.rsplit("@", 1)[1] for value in uses}

    assert len(uses) == 2
    assert len(refs) == 1


def test_dependabot_groups_codeql_version_and_security_updates():
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    github_actions = next(
        update for update in config["updates"] if update["package-ecosystem"] == "github-actions"
    )
    groups = github_actions["groups"]

    assert groups["codeql-action"] == {
        "applies-to": "version-updates",
        "patterns": ["github/codeql-action/*"],
    }
    assert groups["codeql-action-security"] == {
        "applies-to": "security-updates",
        "patterns": ["github/codeql-action/*"],
    }
