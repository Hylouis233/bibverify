# Bibverify

<!-- mcp-name: io.github.Hylouis233/bibverify -->

<p align="center">
  <strong>Verify, repair, and enrich BibTeX references with confidence.</strong>
</p>

<p align="center">
  <a href="README.md">中文</a> · <a href="#quick-start">Quick start</a> · <a href="#mcp-and-ai-assistants">MCP</a> · <a href="#development">Development</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/v/bibverify.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/pyversions/bibverify.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml"><img src="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

Bibverify is a BibTeX verification tool for researchers, editors, automation, and AI assistants. It starts with an exact DOI lookup when possible, dynamically ranks metadata providers from identifiers and subject hints, and accepts a candidate only after title-similarity checks.

Your source `.bib` file is never overwritten in place. Bibverify writes a report, a byte-for-byte backup, an updated bibliography, and a separate file for entries that need manual attention.

## Highlights

- DOI-first lookup through Crossref, with title lookup as a fallback.
- Crossref, OpenAlex, Semantic Scholar, PubMed, Europe PMC, CORE, DBLP, arXiv, bioRxiv, and more.
- Conservative title matching based on sequence similarity, token overlap, and relative length.
- A shared connection pool with retries, exponential backoff, and `Retry-After` support for `429/5xx` responses.
- Cross-platform path, encoding, Unicode filename, UTF-8 BOM, and CRLF handling.
- JSON output, stable exit codes, a Python API, and an MCP server built on the official SDK.
- Atomic output writes and byte-preserving backups.

## Requirements

- Python 3.11–3.14
- Windows, macOS, or Linux
- Network access to the enabled metadata APIs

GitHub Actions tests all three operating systems across all four supported Python versions.

## Quick start

### Install

For a globally available CLI in an isolated environment, use `pipx` or `uv tool`:

```bash
pipx install bibverify
```

```bash
uv tool install bibverify
```

Inside a virtual environment, regular pip also works:

```bash
python -m pip install --upgrade bibverify
```

Each release also provides native, smoke-tested standalone packages for Windows, macOS, and Linux on GitHub Releases.

### Convert a DOI to BibTeX

```bash
bibverify doi 10.1038/nature12373 --key example2013
```

For a machine-readable response:

```bash
bibverify doi 10.1038/nature12373 --json
```

### Verify a `.bib` file

Create a starter configuration:

```bash
bibverify config init
```

Place `references.bib` next to the configuration and run:

```bash
bibverify check --config config.json
```

You can override the input and output paths from the command line:

```bash
bibverify check references.bib --config config.json --output-dir bibverify-output
```

PowerShell example:

```powershell
py -m bibverify check '.\Bibliography\references.bib' --output-dir '.\Verification results'
```

The v0.2 forms remain available for compatibility, although new scripts should use subcommands:

```bash
bibverify config.json
bibverify --doi 10.1038/nature12373 --key example2013
```

## Configuration

A minimal configuration looks like this:

```json
{
  "language": "EN",
  "bib_file": "references.bib",
  "encoding": "auto",
  "output_dir": "bibverify-output",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

See [`config_template.json`](config_template.json) for every commonly used option.

Path behavior is intentionally predictable:

- Relative `bib_file` and `output_dir` values are resolved from the directory containing `config.json`, not the shell's current directory.
- If `output_dir` is omitted, output is written next to the input bibliography.
- `encoding: "auto"` tries UTF-8 with BOM, UTF-8, and GB18030. It does not fall back to Latin-1 and silently turn unknown bytes into mojibake.

### API keys and email

Keys can be stored in a local configuration, but environment variables are safer and harder to commit accidentally:

| Environment variable | Used for |
|---|---|
| `BIBVERIFY_EMAIL` | Crossref polite pool and contact information |
| `BIBVERIFY_OPENALEX_API_KEY` | OpenAlex |
| `BIBVERIFY_SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar |
| `BIBVERIFY_PUBMED_API_KEY` | PubMed/NCBI |
| `BIBVERIFY_CORE_API_KEY` | CORE |

PowerShell:

```powershell
$env:BIBVERIFY_EMAIL = 'you@example.com'
$env:BIBVERIFY_OPENALEX_API_KEY = '...'
bibverify check --config config.json
```

Bash or Zsh:

```bash
export BIBVERIFY_EMAIL='you@example.com'
export BIBVERIFY_OPENALEX_API_KEY='...'
bibverify check --config config.json
```

### Query and matching settings

```json
{
  "query_settings": {
    "delay_between_requests": 0.5,
    "timeout": 10,
    "max_retries": 3,
    "backoff_factor": 0.5,
    "stop_on_first_match": true,
    "title_match_threshold": 0.86
  }
}
```

A higher title threshold is more conservative. Values below `0.80` are not recommended unless you understand the false-match risk.

## CLI reference

```text
bibverify check [BIB_FILE] [--config PATH] [--output-dir DIR] [--json]
bibverify doi DOI [--key KEY] [--config PATH] [--json]
bibverify config init [--output PATH] [--force]
bibverify doctor [--config PATH] [--json]
bibverify providers list [--json]
bibverify mcp [--config PATH] [--transport stdio|streamable-http]
bibverify agent init [--target generic|codex|claude|cursor]
bibverify skill export [--target ...]
```

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Verification completed successfully |
| `1` | Completed, but one or more entries were not found |
| `2` | Configuration, path, encoding, or argument error |
| `3` | One or more entries failed during processing |

With `--json`, stdout contains JSON only. Diagnostics go to stderr, which keeps the command safe for CI and scripts.

## Output files

For an input named `references.bib`, Bibverify may create:

- `bib_check_report_<timestamp>.txt`: summary and field-level differences.
- `references_backup_<timestamp>.bib`: byte-for-byte copy of the source.
- `references_updated_<timestamp>.bib`: complete, ready-to-use bibliography with accepted updates; omitted when no entries change.
- `references_wrong_<timestamp>.bib`: entries that were not found or failed; omitted when no entries need attention.

Each output can be disabled independently through `output_settings`.

## Provider ranking

Static priority is only the starting point:

1. A DOI promotes Crossref and uses its exact DOI endpoint first.
2. PMID, PMCID, or biomedical hints promote PubMed and Europe PMC.
3. An arXiv identifier promotes arXiv.
4. Computer-science venue hints promote DBLP.

Unpaywall is currently treated as open-access enrichment, not as a primary bibliographic metadata provider.

## MCP and AI assistants

Bibverify uses the official MCP Python SDK and supports local stdio and Streamable HTTP transports.

Start a stdio server:

```bash
bibverify mcp --config config.json
```

MCP client configuration:

```json
{
  "mcpServers": {
    "bibverify": {
      "command": "bibverify",
      "args": ["mcp", "--config", "config.json"]
    }
  }
}
```

Start Streamable HTTP:

```bash
bibverify mcp --transport streamable-http --config config.json
```

Available tools:

- `doi_to_bibtex`
- `rank_lookup_sources`
- `explain_update_diff`
- `verify_bib_file`

Generate setup files for Codex, Claude, Cursor, or a generic MCP client:

```bash
bibverify agent init --target codex --output .bibverify-agent --config config.json
bibverify doctor --config config.json
```

## Python API

```python
from bibverify.checker import BibTeXChecker

checker = BibTeXChecker("config.json")
summary = checker.run()
print(summary["counts"])
```

`from bib_check import BibTeXChecker` remains compatible during the 0.3 release line, but new code should use the package import above.

## Development

```bash
git clone https://github.com/Hylouis233/bibverify.git
cd bibverify
python -m venv .venv
```

After activating the environment:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests bib_check.py
python -m ruff format --check src tests bib_check.py
python -m mypy
python -m build
python -m twine check dist/*
```

CI tests Windows, macOS, and Linux on Python 3.11–3.14, plus dedicated lint, strict type checks for modern interface boundaries, coverage, and packaging jobs. Releases use PyPI Trusted Publishing, so no upload token is stored in the repository.

## Citation

If Bibverify supports your research, please cite:

```bibtex
@software{bibverify2025,
  title = {Bibverify: A Multi-Platform BibTeX Reference Verification Tool},
  author = {Hong Liu},
  year = {2025},
  url = {https://github.com/Hylouis233/bibverify},
  doi = {10.5281/zenodo.17338090}
}
```

## License

[MIT License](LICENSE)
