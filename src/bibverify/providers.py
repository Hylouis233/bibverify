"""Provider registry shared by the CLI and verification engine."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

PROVIDER_NAMES = (
    "crossref",
    "openalex",
    "semantic_scholar",
    "pubmed",
    "europe_pmc",
    "core",
    "unpaywall",
    "dblp",
    "arxiv",
    "biorxiv",
    "base",
    "google_scholar",
)


def build_provider_registry(checker: Any) -> dict[str, Callable[..., Any]]:
    """Bind enabled provider names to their query implementation."""
    method_names = {
        "arxiv": "query_arxiv",
        "openalex": "query_openalex",
        "semantic_scholar": "query_semantic_scholar",
        "dblp": "query_dblp",
        "pubmed": "query_pubmed",
        "europe_pmc": "query_europe_pmc",
        "core": "query_core",
        "base": "query_base",
        "biorxiv": "query_biorxiv",
        "google_scholar": "query_google_scholar",
    }
    return {
        name: (lambda title, method=method: getattr(checker, method)(title))
        for name, method in method_names.items()
    }
