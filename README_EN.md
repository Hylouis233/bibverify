# Bibverify - BibTeX Reference Verification Tool

<!-- mcp-name: io.github.Hylouis233/bibverify -->

<p align="center">
<a href="README_EN.md"><img src="https://img.shields.io/badge/English-README-blue.svg" alt="English README"></a> | <a href="README.md"><img src="https://img.shields.io/badge/中文-README-red.svg" alt="中文 README"></a>
</p>

> **English**: A multi-platform BibTeX reference verification and update tool with DOI-first lookup, dynamic source ranking, MCP tools, and skill export for AI assistants.
>
> **Chinese**: 一个支持多平台的 BibTeX 文献验证和更新工具，通过 DOI 精确查询、动态检索排序和多个学术数据库 API 自动检查、补全和解释文献信息。

[![PyPI](https://img.shields.io/pypi/v/bibverify.svg)](https://pypi.org/project/bibverify/) [![Release](https://img.shields.io/github/v/release/Hylouis233/bibverify)](https://github.com/Hylouis233/bibverify/releases) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/) [![Stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social)](https://github.com/Hylouis233/bibverify) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17338090.svg)](https://doi.org/10.5281/zenodo.17338090)

## Quick Start

### Install

```bash
pip install -U bibverify
```

### DOI to BibTeX

```bash
bibverify --doi 10.1038/nature12373 --key example2013
```

### Verify a `.bib` file

Create `config.json`:

```json
{
  "language": "EN",
  "bib_file": "references.bib",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

Then run:

```bash
bibverify config.json
```

### Generate AI assistant integration files

```bash
bibverify agent init --target codex --output .bibverify-agent --config config.json
bibverify agent doctor --config config.json
```

The generated `.bibverify-agent/` directory includes an MCP configuration snippet, `SKILL.md`, and local setup notes.

## Key Features

- DOI first: entries with a DOI use exact Crossref lookup before falling back to title search.
- Dynamic source ranking: DOI, PMID/PMCID, arXiv, and field hints promote Crossref, PubMed, Europe PMC, arXiv, and DBLP.
- Multi-platform verification: Crossref, OpenAlex, Semantic Scholar, PubMed, Europe PMC, CORE, DBLP, arXiv, bioRxiv, and related sources.
- AI assistant integration: built-in MCP stdio server and skill export for Codex, Claude, Cursor, and other MCP-enabled assistants.
- Safe outputs: the source `.bib` file is not overwritten in place; Bibverify writes backup, updated, and problem-entry files.

## 🚀 Supported Academic Platforms

| Platform | Priority | Discipline Coverage | API Requirement | Special Feature |
|------|--------|----------|---------|----------|
| **CrossRef** | 1 | All disciplines | No API | Polite Pool |
| **OpenAlex** | 2 | All disciplines | API key recommended/required | Citation graph |
| **Semantic Scholar** | 3 | All disciplines | API recommended | AI-driven |
| **PubMed** | 4 | Biomedicine | Optional API | Medical focus |
| **Europe PMC** | 5 | Biomedicine | No API | European medical |
| **CORE** | 6 | Open access | API recommended | Open papers |
| **Unpaywall** | Enrichment | All disciplines | Email required | Open-version enrichment, not a primary metadata source |
| **DBLP** | 8 | Computer Science | No API | CS-focused |
| **arXiv** | 9 | Preprints | No API | Preprints |
| **bioRxiv** | 10 | Biomedical preprints | No API | Biomedical preprints |

## 📦 Installation

### Install from PyPI

```bash
pip install -U bibverify
```

### Develop or run from source

```bash
git clone https://github.com/Hylouis233/bibverify.git
cd bibverify
pip install -e .
```

If you only need the runtime dependencies:

```bash
pip install -r requirements.txt
```

Current release pages:

- PyPI: https://pypi.org/project/bibverify/
- GitHub Releases: https://github.com/Hylouis233/bibverify/releases

## ⚙️ Configuration

### 1. Create a config file

After installing from PyPI, create a minimal `config.json` manually:

```json
{
  "language": "EN",
  "bib_file": "references.bib",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

If you are working from a source checkout, you can copy the template and edit it:

```bash
cp config_template.json config.json
```

### 2. Basic settings

Edit `config.json`:

```json
{
  "language": "EN",
  "bib_file": "references.bib",
  "user_info": {
    "email": "your_email@example.com",
    "app_name": "Bibverify"
  }
}
```

### 3. Platform settings

Enable/disable platforms as needed:

```json
{
  "platforms": {
    "crossref": {
      "enabled": true,
      "priority": 1,
      "use_polite_pool": true
    },
    "semantic_scholar": {
      "enabled": true,
      "priority": 3,
      "requires_api_key": true,
      "api_key": "your_api_key_here"
    }
  }
}
```

### 4. Language

- `"CN"`: Chinese UI
- `"EN"`: English UI

## 🎯 Usage

### Command quick reference

| Command | Purpose |
|------|------|
| `bibverify config.json` | Verify a `.bib` file using a config file |
| `bibverify --doi DOI --key KEY` | Generate one BibTeX entry from a DOI |
| `bibverify mcp --config config.json` | Start the MCP stdio server |
| `bibverify agent init --target codex` | Generate MCP/Skill integration files |
| `bibverify agent doctor --config config.json` | Check local integration readiness |
| `bibverify skill export --target codex` | Export only `SKILL.md` |

### Verify a `.bib` file

```bash
bibverify config.json
```

### Generate one BibTeX entry from a DOI

```bash
bibverify --doi 10.1038/nature12373 --key example2013
```

This mode queries Crossref by exact DOI and prints a BibTeX entry.

### One-Step AI / MCP / Skill Integration

Create local integration files for beginner users:

```bash
bibverify agent init --target codex --output .bibverify-agent --config config.json
```

Generated files:

- `.bibverify-agent/SKILL.md`: Bibverify instructions for an AI assistant
- `.bibverify-agent/mcp.json`: MCP server configuration snippet
- `.bibverify-agent/README.md`: Local integration notes

Start the MCP stdio server:

```bash
bibverify mcp --config config.json
```

Export only the skill file:

```bash
bibverify skill export --target codex --output .bibverify-agent/SKILL.md
```

Check local readiness:

```bash
bibverify agent doctor --config config.json
```

The MCP server currently exposes four tools: `doi_to_bibtex`, `rank_lookup_sources`, `explain_update_diff`, and `verify_bib_file`. Once an AI client has the MCP server configured, it can call these tools for DOI-to-BibTeX conversion, lookup-order explanation, entry-diff explanation, and `.bib` file verification.

Copyable MCP configuration snippet:

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

## 📁 Output Files

The program will generate the following files. The current version uses the fixed `sample_` prefix for generated `.bib` outputs and does not overwrite your source file in place:

1. **Check report** (`bib_check_report_YYYYMMDD_HHMMSS.txt`)
   - List of references that passed verification
   - References that need updates with detailed differences
   - List of references not found

2. **Backup file** (`sample_backup_YYYYMMDD_HHMMSS.bib`)
   - Full backup of the original BibTeX file

3. **Updated file** (`sample_updated_YYYYMMDD_HHMMSS.bib`)
   - All updated reference entries

4. **Problem file** (`sample_wrong_YYYYMMDD_HHMMSS.bib`)
   - Entries not found or failed during processing

## 🔄 Workflow

```
Start
 ↓
Load BibTeX file
 ↓
For each entry:
 ├─ Extract title
 ├─ Re-rank platforms from DOI/PMID/arXiv identifiers
 ├─ Query platforms by adjusted priority
 ├─ Intelligently match bibliographic info
 ├─ Preserve original key
 ├─ Compare field differences
 └─ Record results
 ↓
Generate check report
 ↓
Generate updated file
 ↓
Done
```

## 📝 BibTeX Formatting Standards

### Field order

The generated BibTeX files follow a standard field order:

```bibtex
@article{key,
  title={...},
  author={...},
  journal={...},
  volume={...},
  number={...},
  pages={...},
  year={...},
  publisher={...},
  doi={...}
}
```

### Reference type mapping

| Platform Type | BibTeX Type |
|----------|------------|
| journal-article | article |
| book-chapter | incollection |
| book | book |
| proceedings-article | inproceedings |
| posted-content | unpublished |

## 🎯 Intelligent Matching Rules

### Title matching strategy

1. **Exact match** (case- and punctuation-insensitive)
2. **Original title is a substring of the new title**
3. **Strict non-match**: avoid false positives

### Title normalization steps

```
"{{Detecting Influenza Epidemics}}"
↓ Remove braces
"Detecting Influenza Epidemics"
↓ Lowercase
"detecting influenza epidemics"
↓ Remove punctuation
"detecting influenza epidemics"
↓ Normalize whitespace
"detecting influenza epidemics"
```

## 🔧 Advanced Settings

### API settings

Some platforms require an API key for higher rate limits or stable access:

#### OpenAlex
```json
"openalex": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://docs.openalex.org/how-to-use-the-api/getting-started/authentication

#### Semantic Scholar
```json
"semantic_scholar": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://www.semanticscholar.org/product/api#api-key-form

#### PubMed
```json
"pubmed": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://www.ncbi.nlm.nih.gov/account/

#### CORE
```json
"core": {
  "api_key": "your_api_key_here"
}
```
Registration page: https://core.ac.uk/services/api

### Polite Pool

For better throughput, set your email:

```json
"user_info": {
  "email": "your_email@example.com"
}
```

### Query settings

```json
"query_settings": {
  "delay_between_requests": 0.5,
  "timeout": 10,
  "max_retries": 3,
  "stop_on_first_match": true
}
```

The effective lookup order is not only the static table order. Entries with a DOI are promoted to Crossref DOI lookup first; entries with PMID/PMCID promote PubMed and Europe PMC; entries with an arXiv identifier promote arXiv. Unpaywall is currently treated as open-access enrichment, not as a primary bibliographic metadata source.

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/Hylouis233/bibverify?style=social) ![GitHub forks](https://img.shields.io/github/forks/Hylouis233/bibverify?style=social) ![GitHub issues](https://img.shields.io/github/issues/Hylouis233/bibverify) ![GitHub pull requests](https://img.shields.io/github/issues-pr/Hylouis233/bibverify)

[![Star History Chart](https://api.star-history.com/svg?repos=Hylouis233/bibverify&type=Date)](https://www.star-history.com/#Hylouis233/bibverify&Date)

## 📖 Academic Citation

If you use Bibverify in your research or project, please cite it:

### BibTeX
```bibtex
@software{bibverify2025,
  title={Bibverify: A Multi-Platform BibTeX Reference Verification Tool},
  author={Hong Liu},
  year={2025},
  url={https://github.com/Hylouis233/bibverify},
  note={DOI: 10.5281/zenodo.17338090}
}
```

### Text
```
Hong Liu. (2025). Bibverify: A Multi-Platform BibTeX Reference Verification Tool. 
GitHub. https://github.com/Hylouis233/bibverify. DOI: 10.5281/zenodo.17338090
```

**Bibverify** - Make reference management simpler and more accurate!

⭐ **If this tool helps you, please give it a star!**



## 🤝 Contributing

Contributions are welcome via [GitHub Issues](https://github.com/Hylouis233/bibverify/issues) and [Pull Requests](https://github.com/Hylouis233/bibverify/pulls)!
