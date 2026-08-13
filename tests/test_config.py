import json
from pathlib import Path

import pytest

from bibverify.config import create_config, load_config


def test_relative_paths_resolve_from_config_directory(tmp_path, monkeypatch):
    project = tmp_path / "项目 with spaces"
    project.mkdir()
    (project / "references.bib").write_text("", encoding="utf-8")
    config_path = project / "config.json"
    config_path.write_text(
        json.dumps({"bib_file": "references.bib", "output_dir": "results"}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    config, resolved = load_config(config_path)

    assert resolved == config_path.resolve()
    assert Path(config["bib_file"]) == (project / "references.bib").resolve()
    assert Path(config["output_dir"]) == (project / "results").resolve()


def test_environment_secrets_override_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"platforms": {"openalex": {"api_key": "stored"}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("BIBVERIFY_OPENALEX_API_KEY", "from-env")
    monkeypatch.setenv("BIBVERIFY_EMAIL", "mail@example.com")

    config, _ = load_config(config_path)

    assert config["platforms"]["openalex"]["api_key"] == "from-env"
    assert config["user_info"]["email"] == "mail@example.com"


def test_utf8_bom_config_and_validation(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"language":"EN","query_settings":{"timeout":12}}', encoding="utf-8-sig"
    )

    config, _ = load_config(config_path)

    assert config["language"] == "EN"
    assert config["query_settings"]["timeout"] == 12
    assert config["query_settings"]["read_timeout"] == 12


def test_create_config_will_not_overwrite_without_force(tmp_path):
    output = tmp_path / "config.json"
    create_config(output)

    with pytest.raises(FileExistsError):
        create_config(output)

    create_config(output, force=True)
    assert json.loads(output.read_text(encoding="utf-8"))["encoding"] == "auto"
