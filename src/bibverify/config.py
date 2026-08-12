"""Configuration loading, validation, and cross-platform path handling."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "crossref": {"enabled": True, "priority": 1, "use_polite_pool": True},
    "openalex": {"enabled": True, "priority": 2, "api_key": ""},
    "semantic_scholar": {"enabled": True, "priority": 3, "api_key": ""},
    "pubmed": {"enabled": True, "priority": 4, "api_key": ""},
    "europe_pmc": {"enabled": True, "priority": 5},
    "core": {"enabled": False, "priority": 6, "api_key": ""},
    "unpaywall": {"enabled": False, "priority": 7},
    "dblp": {"enabled": True, "priority": 8},
    "arxiv": {"enabled": True, "priority": 9},
    "biorxiv": {"enabled": True, "priority": 10},
    "base": {"enabled": False, "priority": 11},
    "google_scholar": {"enabled": False, "priority": 99},
}

DEFAULT_CONFIG: dict[str, Any] = {
    "language": "CN",
    "bib_file": "references.bib",
    "encoding": "auto",
    "output_dir": None,
    "user_info": {"email": "research@example.com", "app_name": "Bibverify"},
    "platforms": PROVIDER_DEFAULTS,
    "query_settings": {
        "delay_between_requests": 0.5,
        "timeout": 10.0,
        "max_retries": 3,
        "backoff_factor": 0.5,
        "stop_on_first_match": True,
        "title_match_threshold": 0.86,
    },
    "output_settings": {
        "generate_report": True,
        "generate_backup": True,
        "generate_updated_bib": True,
        "generate_wrong_bib": True,
        "report_format": "txt",
        "timestamp_format": "%Y%m%d_%H%M%S",
    },
}

API_KEY_ENV = {
    "openalex": "BIBVERIFY_OPENALEX_API_KEY",
    "semantic_scholar": "BIBVERIFY_SEMANTIC_SCHOLAR_API_KEY",
    "pubmed": "BIBVERIFY_PUBMED_API_KEY",
    "core": "BIBVERIFY_CORE_API_KEY",
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge mappings without mutating either input."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_path(value: str | Path, base_dir: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve(strict=False))


def load_config(
    config_file: str | Path = "config.json",
    *,
    overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path]:
    """Load a configuration and resolve paths relative to that config file."""
    requested = Path(config_file).expanduser()
    config_path = requested.resolve(strict=False)
    base_dir = config_path.parent
    user_config: dict[str, Any] = {}
    if requested.exists():
        with requested.open("r", encoding="utf-8-sig") as stream:
            parsed = json.load(stream)
        if not isinstance(parsed, dict):
            raise ValueError("Configuration root must be a JSON object.")
        user_config = parsed

    config = deep_merge(DEFAULT_CONFIG, user_config)
    if overrides:
        config = deep_merge(config, overrides)

    language = str(config.get("language", "CN")).upper()
    if language not in {"CN", "EN"}:
        raise ValueError("language must be either 'CN' or 'EN'.")
    config["language"] = language

    query = config["query_settings"]
    if float(query["timeout"]) <= 0:
        raise ValueError("query_settings.timeout must be greater than zero.")
    if int(query["max_retries"]) < 0:
        raise ValueError("query_settings.max_retries cannot be negative.")
    if float(query["delay_between_requests"]) < 0:
        raise ValueError("query_settings.delay_between_requests cannot be negative.")
    threshold = float(query["title_match_threshold"])
    if not 0 <= threshold <= 1:
        raise ValueError("query_settings.title_match_threshold must be between zero and one.")

    config["bib_file"] = _resolve_path(config["bib_file"], base_dir)
    output_dir = config.get("output_dir")
    config["output_dir"] = (
        _resolve_path(output_dir, base_dir) if output_dir else str(Path(config["bib_file"]).parent)
    )

    email = os.getenv("BIBVERIFY_EMAIL")
    if email:
        config["user_info"]["email"] = email
    for provider, env_name in API_KEY_ENV.items():
        if value := os.getenv(env_name):
            config["platforms"].setdefault(provider, {})["api_key"] = value

    return config, config_path


def starter_config() -> dict[str, Any]:
    """Return a compact, fully functional starter configuration."""
    return {
        "language": "CN",
        "bib_file": "references.bib",
        "encoding": "auto",
        "output_dir": "bibverify-output",
        "user_info": {"email": "your_email@example.com", "app_name": "Bibverify"},
        "platforms": {
            "crossref": {"enabled": True, "priority": 1},
            "openalex": {"enabled": True, "priority": 2, "api_key": ""},
            "semantic_scholar": {"enabled": True, "priority": 3, "api_key": ""},
        },
        "query_settings": deepcopy(DEFAULT_CONFIG["query_settings"]),
        "output_settings": deepcopy(DEFAULT_CONFIG["output_settings"]),
    }


def create_config(output: str | Path, *, force: bool = False) -> Path:
    """Write a starter configuration without replacing files accidentally."""
    path = Path(output).expanduser().resolve(strict=False)
    if path.exists() and not force:
        raise FileExistsError(f"Configuration already exists: {path}. Use --force to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(starter_config(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path
