import tomllib
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


def test_bibtexparser_requirement_preserves_the_supported_v1_api():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirement = next(
        value for value in metadata["project"]["dependencies"] if value.startswith("bibtexparser")
    )
    compatibility_requirements = (
        (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    )

    # Remove this guard only with a tested migration of checker.py and bibtex.py to v2.
    assert "<2" in requirement.removeprefix("bibtexparser").split(",")
    assert requirement in compatibility_requirements


def test_dependabot_defers_only_bibtexparser_major_version_updates():
    config = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text(encoding="utf-8"))
    pip = next(
        update
        for update in config["updates"]
        if update["package-ecosystem"] == "pip" and update["directory"] == "/"
    )

    # A version range or dependency-only ignore would also suppress security updates.
    # Remove this exception with the tested v2 API migration, alongside the <2 guard.
    assert pip["ignore"] == [
        {
            "dependency-name": "bibtexparser",
            "update-types": ["version-update:semver-major"],
        }
    ]
    assert "allow" not in pip
    assert pip.get("open-pull-requests-limit", 5) > 0
