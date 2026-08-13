from tools.validate_project import (
    validate_action_pins,
    validate_json,
    validate_markdown_links,
    validate_toml,
    validate_yaml,
)


def test_project_metadata_and_links_are_valid():
    validate_json()
    validate_toml()
    validate_yaml()
    validate_action_pins()
    validate_markdown_links()
