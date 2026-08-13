"""Helpers for configuring AI-assistant integrations."""

import json
import os
import sys
from pathlib import Path

import bibtexparser
import mcp
import requests

from bibverify.config import load_config

SUPPORTED_TARGETS = ("generic", "codex", "claude", "cursor")


def build_skill_markdown(target="generic", config_file="config.json"):
    target_note = {
        "generic": "Use this skill with any MCP-capable assistant.",
        "codex": "Use this skill from Codex after adding the Bibverify MCP server to your Codex MCP configuration.",
        "claude": "Use this skill from Claude after adding the Bibverify MCP server to your Claude MCP configuration.",
        "cursor": "Use this skill from Cursor after adding the Bibverify MCP server to your Cursor MCP configuration.",
    }.get(target, "Use this skill with any MCP-capable assistant.")

    return f"""---
name: bibverify
description: Verify, repair, and generate BibTeX references through the Bibverify MCP tools.
---

# Bibverify

{target_note}

## When To Use

- The user asks to verify a `.bib` file, BibTeX entry, DOI, citation, bibliography, or reference list.
- The user asks whether a BibTeX entry is correct or wants fields completed from academic metadata.
- The user asks for a BibTeX entry from a DOI.

## Available MCP Tools

- `doi_to_bibtex`: Convert one DOI into a BibTeX entry using Crossref metadata.
- `rank_lookup_sources`: Explain the source lookup order Bibverify will use for an entry.
- `explain_update_diff`: Compare two BibTeX-like entry objects and return field differences.
- `verify_bib_file`: Run Bibverify against a config file and return a summary plus generated file names.

## Workflow

1. Prefer `doi_to_bibtex` when the user gives a DOI.
2. Use `rank_lookup_sources` before a full verification when the user asks why a source is queried first.
3. Use `verify_bib_file` for project-level `.bib` verification. The default config file is `{config_file}`.
4. Explain any changed fields in plain language. Do not silently overwrite the user's source `.bib`; default verification writes timestamped reports, backups, updated proposals, and manual-review files. Only an explicit `--apply` changes the source.
5. Distinguish `not_found` from `source_unavailable`, and do not call an unindexed reference fake or fabricated.

## Example User Requests

- "把这个 DOI 转成 BibTeX: 10.1038/nature12373"
- "检查 references.bib 里哪些文献需要更新"
- "为什么这个条目优先查 Crossref 而不是 OpenAlex?"
- "比较这两个 BibTeX 条目的差异"
"""


def build_mcp_config(config_file="config.json"):
    return {
        "mcpServers": {
            "bibverify": {
                "command": "bibverify",
                "args": ["mcp", "--config", config_file],
            }
        }
    }


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def export_skill(target="generic", output=None, config_file="config.json"):
    if target not in SUPPORTED_TARGETS:
        raise ValueError("target must be one of: " + ", ".join(SUPPORTED_TARGETS))

    content = build_skill_markdown(target=target, config_file=config_file)
    if output:
        output_path = Path(output)
        if output_path.exists() and output_path.is_dir():
            output_path = output_path / "SKILL.md"
        write_text(output_path, content)
        return str(output_path)

    sys.stdout.write(content)
    return None


def init_agent(target="generic", output=".bibverify-agent", config_file="config.json"):
    if target not in SUPPORTED_TARGETS:
        raise ValueError("target must be one of: " + ", ".join(SUPPORTED_TARGETS))

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    skill_path = output_dir / "SKILL.md"
    mcp_path = output_dir / "mcp.json"
    readme_path = output_dir / "README.md"

    write_text(skill_path, build_skill_markdown(target=target, config_file=config_file))
    write_text(
        mcp_path,
        json.dumps(build_mcp_config(config_file=config_file), ensure_ascii=False, indent=2) + "\n",
    )
    write_text(
        readme_path,
        f"""# Bibverify Agent Integration

This folder contains a ready-to-copy MCP configuration and a skill prompt for Bibverify.

## Files

- `SKILL.md`: Skill instructions for an AI assistant.
- `mcp.json`: MCP server configuration snippet.

## MCP Command

```bash
bibverify mcp --config {config_file}
```

## Quick Smoke Test

```bash
bibverify agent doctor --config {config_file}
bibverify --doi 10.1038/nature12373 --key example2013
```
""",
    )
    return [str(skill_path), str(mcp_path), str(readme_path)]


def doctor(config_file="config.json"):
    checks = []

    def add(name, ok, detail, *, required=False):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "required": required})

    add("python", sys.version_info >= (3, 11), sys.version.split()[0], required=True)
    add("bibtexparser", True, getattr(bibtexparser, "__version__", "installed"), required=True)
    add("requests", True, getattr(requests, "__version__", "installed"), required=True)
    add("mcp", True, getattr(mcp, "__version__", "installed"), required=True)

    config_path = Path(config_file).expanduser().resolve(strict=False)
    config_exists = config_path.exists()
    add(
        "config",
        config_exists,
        config_file if config_exists else "missing; Bibverify will use defaults",
    )

    if config_exists:
        try:
            config, _ = load_config(config_path)
            add("config-json", True, "valid JSON", required=True)
            bib_path = Path(config["bib_file"])
            add("bib-file", bib_path.is_file(), str(bib_path), required=True)
            output_dir = Path(config["output_dir"])
            writable_parent = next(
                (path for path in [output_dir, *output_dir.parents] if path.exists()), None
            )
            add(
                "output-dir",
                writable_parent is not None and os.access(writable_parent, os.W_OK),
                str(output_dir),
                required=True,
            )
            for provider, settings in config.get("platforms", {}).items():
                if not settings.get("enabled"):
                    continue
                if provider == "core":
                    add(
                        "provider-core-key",
                        bool(settings.get("api_key")),
                        "configured"
                        if settings.get("api_key")
                        else "missing BIBVERIFY_CORE_API_KEY",
                        required=True,
                    )
                elif provider in {"openalex", "semantic_scholar", "pubmed"}:
                    add(
                        f"provider-{provider}-key",
                        True,
                        "configured" if settings.get("api_key") else "optional key not configured",
                    )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            add("config-json", False, str(exc), required=True)

    add("mcp-command", True, f"bibverify mcp --config {config_file}")
    return checks


def format_doctor_report(checks):
    lines = ["Bibverify agent doctor"]
    for check in checks:
        status = "OK" if check["ok"] else ("ERROR" if check.get("required") else "WARN")
        lines.append(f"[{status}] {check['name']}: {check['detail']}")
    return "\n".join(lines)
