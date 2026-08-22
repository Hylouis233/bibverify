# Bibverify

<!-- mcp-name: io.github.Hylouis233/bibverify -->

<p align="center">
  <strong>Verify bibliographic existence and metadata consistency without destructive edits.</strong>
</p>

<p align="center">
  <a href="README_CN.md">Chinese</a> · <a href="#install">Install</a> · <a href="#quick-start">Quick start</a> · <a href="#mcp-and-ai-assistants">MCP</a> · <a href="#development">Development</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/v/bibverify.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/bibverify/"><img src="https://img.shields.io/pypi/pyversions/bibverify.svg" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml"><img src="https://github.com/Hylouis233/bibverify/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

Bibverify is a BibTeX metadata verification tool for researchers, editors, automation, and AI assistants. It starts with exact DOI, PMID, PMCID, or arXiv identifiers and then scores candidates from title, author, year, venue, and pagination evidence.

Bibverify evaluates whether a bibliographic record can be located in the queried sources and whether its metadata agrees. It does not prove that research findings are true, data is authentic, or a venue is reputable. A missing database record is not evidence that a reference is fabricated. By default, the source `.bib` file is never overwritten.

## Highlights

- Identifier-first lookup for DOI, PMID, PMCID, and arXiv IDs.
- Crossref, OpenAlex, Semantic Scholar, PubMed, Europe PMC, CORE, DBLP, arXiv, bioRxiv, and more.
- Explainable multi-signal matching across identifiers, title, authors, year, venue, and pages. A resolvable DOI with a materially different title becomes `identifier_conflict` instead of being hidden by title search.
- Structured provider outcomes distinguish a genuine no-match from rate limiting, authentication, network, parsing, and provider failures.
- Non-destructive merging preserves `abstract`, `keywords`, `file`, `note`, and custom fields that providers do not return; conflicting persistent identifiers are never overwritten automatically.
- A shared connection pool with retries, exponential backoff, and `Retry-After` support for `429/5xx` responses.
- An expiring SQLite cache for successful GET responses; failures are never cached.
- Cross-platform path, encoding, Unicode filename, UTF-8 BOM, and CRLF handling.
- JSON output, stable exit codes, a Python API, and an MCP server built on the official SDK.
- Atomic output writes and byte-preserving backups.

## Requirements

- Windows, macOS, or Linux
- Network access to the enabled metadata APIs
- Python 3.11–3.14 when using the Python distribution; npm, containers, and native packages bundle their runtime

GitHub Actions tests all three operating systems across all four supported Python versions.

## Install

The current published release is v0.3.0. This branch prepares v0.4.0; commands marked **v0.4.0**
become usable only after their linked npm, GHCR, or GitHub Release artifact has been published.

Run without a permanent installation:

```bash
uvx bibverify --version
```

Starting with v0.4.0, Node.js users can use the zero-dependency npm launcher. It downloads the
matching native release, verifies `SHA256SUMS`, and forwards every argument and exit code:

```bash
npx --yes @hylouis233/bibverify --version
pnpm dlx @hylouis233/bibverify --version
bunx --bun @hylouis233/bibverify --version
```

For a persistent CLI in an isolated Python environment, use `uv tool` or `pipx`:

```bash
uv tool install bibverify
```

```bash
pipx install bibverify
```

Inside a virtual environment, regular pip also works:

```bash
python -m pip install --upgrade bibverify
```

Each release also provides smoke-tested native packages on
[GitHub Releases](https://github.com/Hylouis233/bibverify/releases). Beginning with v0.4.0, the
release matrix covers Windows x64 plus macOS and glibc 2.28+ Linux on both x64 and ARM64. musl-based
Linux users should use the Python package or container image. Windows ARM64 is not published natively
yet because an MCP runtime dependency does not currently provide Windows ARM64 wheels; npm
automatically uses the tested x64 build under Windows 11 emulation, or you can use the ARM64 container
instead.

The same release publishes a multi-architecture container:

```bash
docker run --rm ghcr.io/hylouis233/bibverify:0.4.0 --version
```

Package-manager manifests are generated from the final release bytes, not from unverified build
inputs. Homebrew, Scoop, and WinGet are not live catalog entries yet: v0.4.0 will attach submission-
ready manifests to GitHub Release, after which each external catalog still requires onboarding or
review. See [Distribution channels](#distribution-channels) for rollout status.

## Quick start

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

Inspect results without writing any file:

```bash
bibverify check references.bib --dry-run --json
```

After reviewing the report, explicitly apply high-confidence field updates. Bibverify creates a byte-for-byte backup first:

```bash
bibverify check references.bib --apply
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
    "connect_timeout": 3.05,
    "read_timeout": 20,
    "max_retries": 3,
    "backoff_factor": 0.5,
    "stop_on_first_match": true,
    "match_threshold": 0.86,
    "ambiguous_threshold": 0.68,
    "auto_update_threshold": 0.92,
    "cache_enabled": true,
    "cache_ttl_hours": 168,
    "cache_path": ".bibverify-cache.sqlite3"
  }
}
```

`connect_timeout` and `read_timeout` separately bound connection setup and response reads; the compatibility `timeout` field remains available. `match_threshold` controls automatic candidate acceptance, `ambiguous_threshold` controls which plausible candidates enter review, and `auto_update_threshold` is an additional gate for field changes. Higher values are more conservative. Relative cache paths are resolved from the config directory.

The official bioRxiv `details` route does not provide arbitrary title search. Bibverify therefore calls bioRxiv only for an exact `10.1101/...` DOI and leaves title-only discovery to providers whose contracts support it, such as Crossref and Europe PMC.

## CLI reference

```text
bibverify check [BIB_FILE] [--config PATH] [--output-dir DIR] [--format txt|json|jsonl|csv] [--dry-run|--apply] [--json]
bibverify doi DOI [--key KEY] [--config PATH] [--json]
bibverify config init [--output PATH] [--force]
bibverify doctor [--config PATH] [--json]
bibverify providers list [--json]
bibverify cache clear [--config PATH]
bibverify benchmark [--dataset PATH]
bibverify mcp [--config PATH] [--workspace-root DIR] [--transport stdio|streamable-http]
bibverify agent init [--target generic|codex|claude|cursor] [--output PATH]
bibverify skill export [--target ...]
```

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | Verification completed and metadata is consistent |
| `1` | Runtime error reserved for uncategorized command failures |
| `2` | Metadata differences or high-confidence updates exist |
| `3` | Ambiguous, not-found, or identifier-conflict entries require review |
| `4` | A provider was unavailable and verification is incomplete |
| `5` | The input file, configuration, or entry is invalid |

With `--json`, stdout contains JSON only. Diagnostics go to stderr, which keeps the command safe for CI and scripts.

## Output files

For an input named `references.bib`, Bibverify may create:

- `bibverify_report_<timestamp>.<format>`: complete states, candidates, provider errors, confidence, and field provenance in `txt`, `json`, `jsonl`, or `csv`.
- `references_backup_<timestamp>.bib`: byte-for-byte copy of the source.
- `references_updated_<timestamp>.bib`: complete bibliography after non-destructive merging; omitted when nothing changes.
- `references_review_<timestamp>.bib`: ambiguous, not-found, unavailable-source, identifier-conflict, or invalid entries; omitted when nothing needs review.

The report-level `complete` value is true only when every entry completed verification. A rate-limited or unreachable provider makes it false even if another source found a candidate. Each `field_diffs` record includes original/suggested values, source, confidence, normalized equivalence, action, and reason.

Each output can be disabled independently through `output_settings`. `--dry-run` overrides those settings and performs zero writes. The default command only writes proposals; only `--apply` changes the source after a backup.

## Provider ranking

Static priority is only the starting point:

1. A DOI promotes Crossref and uses its exact endpoint first. A resolvable DOI with a materially different title stops as `identifier_conflict`.
2. PMID, PMCID, or biomedical hints promote PubMed and Europe PMC.
3. An arXiv identifier promotes arXiv.
4. Computer-science venue hints promote DBLP.

Unpaywall is currently treated as open-access enrichment, not as a primary bibliographic metadata provider. Provider states distinguish `matched`, `no_match`, `ambiguous`, `rate_limited`, `auth_error`, `network_error`, `parse_error`, `provider_error`, and `skipped`.

## MCP and AI assistants

Bibverify uses the official MCP Python SDK and supports local stdio and Streamable HTTP transports.

Start a stdio server:

```bash
bibverify mcp --config config.json --workspace-root .
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

The npm launcher can be used directly by Node-oriented MCP clients:

```json
{
  "mcpServers": {
    "bibverify": {
      "command": "npx",
      "args": ["--yes", "@hylouis233/bibverify", "mcp"]
    }
  }
}
```

Containerized stdio MCP keeps the current directory as the only writable workspace:

```bash
docker run --rm -i -v "$PWD:/workspace" ghcr.io/hylouis233/bibverify:0.4.0 \
  mcp --workspace-root /workspace
```

Start Streamable HTTP:

```bash
bibverify mcp --transport streamable-http --config config.json
```

MCP treats the configuration directory as its workspace root by default. It rejects config or `.bib` reads outside that root and blocks report, cache, or update writes outside it. Broaden access only by explicitly setting `--workspace-root` when starting the server. The official MCP SDK handles protocol negotiation, schemas, structured results, progress, and cancellation.

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

## Distribution channels

| Channel | Command or artifact | Availability |
|---|---|---|
| PyPI | `python -m pip install bibverify` | Published |
| uv | `uvx bibverify` or `uv tool install bibverify` | Published |
| pipx | `pipx install bibverify` | Published |
| npm | `npx --yes @hylouis233/bibverify` | Planned for v0.4.0; not published yet |
| pnpm / Bun | `pnpm dlx @hylouis233/bibverify` / `bunx --bun @hylouis233/bibverify` | Planned for v0.4.0; not published yet |
| GHCR | `docker pull ghcr.io/hylouis233/bibverify:0.4.0` | Planned for v0.4.0; not published yet |
| Native | Windows x64; macOS and glibc 2.28+ Linux x64/ARM64 | Planned for v0.4.0; not published yet |
| Homebrew | Release asset `bibverify.rb` | Submission manifest planned for v0.4.0; catalog not live |
| Scoop | Release asset `bibverify.json` | Submission manifest planned for v0.4.0; catalog not live |
| WinGet | Release assets `Hylouis233.Bibverify*.yaml` | Submission manifests planned for v0.4.0; catalog not live |
| MCP Registry | [`io.github.Hylouis233/bibverify`](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.Hylouis233%2Fbibverify/versions/latest) | Published discovery metadata; install through one of the package entries above |

The npm package is a small launcher rather than a second implementation. The verification engine
remains the same Python codebase across PyPI, npm, native packages, and containers. Release assets
include `SHA256SUMS`; npm verifies the selected binary before execution, and Homebrew, Scoop, and
WinGet manifests pin the same release hashes.

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
python -m ruff check src tests tools bib_check.py
python -m ruff format --check src tests tools bib_check.py
python -m mypy
python -m build
python -m twine check dist/*
python -m bibverify benchmark --dataset benchmarks/cases.json
python -m pip_audit . --strict
(cd npm && npm ci && npm test && npm pack --dry-run)
docker build --tag bibverify:dev .
```

CI tests Windows, macOS, and Linux on Python 3.11–3.14, including provider fixtures, golden write-safety tests, lint, typing, coverage, the offline benchmark, dependency auditing, Python and npm package builds, a container smoke test, and a CycloneDX SBOM. GitHub Actions are pinned to commit SHAs, while the MCP Publisher is version-pinned and SHA-256 verified. PyPI and npm use Trusted Publishing with provenance attestations, and GHCR publishes multi-architecture images with an SBOM and build provenance.

`benchmarks/cases.json` is a small offline regression set covering short-title false positives, DOI conflicts, preprint title variants, Unicode/LaTeX, and fabricated author combinations. It is not a complete scientific evaluation and its scores must not be interpreted as real-world performance ceilings. Contributions of broader, redistributable, human-labeled cases are welcome.

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
