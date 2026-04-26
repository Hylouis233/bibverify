---
name: bibverify
description: Verify, repair, explain, and generate BibTeX references with Bibverify's DOI-first CLI and MCP tools.
metadata:
  openclaw:
    requires:
      bins:
        - bibverify
---

# Bibverify

Use this skill when the user asks to verify a `.bib` file, repair BibTeX metadata, generate BibTeX from a DOI, explain why a reference lookup source was chosen, or compare original vs updated BibTeX fields.

## Preferred Path

If the Bibverify MCP server is available, call its tools directly:

- `doi_to_bibtex`: Convert a DOI, DOI URL, or DOI-prefixed value to BibTeX.
- `rank_lookup_sources`: Explain the effective lookup order for a title and optional BibTeX entry.
- `explain_update_diff`: Compare original and updated BibTeX-like entry objects.
- `verify_bib_file`: Verify a `.bib` file through a Bibverify config file.

Prefer `doi_to_bibtex` for one DOI. Prefer `verify_bib_file` for project-level reference checks.

## CLI Fallback

If MCP is not configured but the `bibverify` command is available:

```bash
bibverify --doi 10.1038/nature12373 --key example2013
bibverify config.json
```

For first-time setup, tell the user to install Bibverify from PyPI and create a minimal config:

```bash
pip install -U bibverify
```

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

## Safety

- Do not silently overwrite the source `.bib` file.
- Tell the user that Bibverify writes timestamped backup, updated, and problem-entry files using the input `.bib` filename stem.
- Do not invent missing bibliographic metadata. Use Bibverify results and explain uncertainty when sources disagree.
- Do not expose API keys or local config secrets in the answer.

## Response Style

Summarize what Bibverify checked, which sources were used or preferred, which entries changed, and where generated files were written. For user-facing explanations, focus on DOI-first lookup, dynamic source ranking, field differences, and remaining entries that need manual review.
