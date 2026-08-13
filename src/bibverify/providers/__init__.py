"""Metadata-provider registry.

Each provider owns its API contract while the verifier consumes one shared
``ProviderResult`` model. Adding a provider no longer requires editing the
verification workflow.
"""

from __future__ import annotations

from typing import Any

from bibverify.providers.arxiv import ArxivProvider
from bibverify.providers.base import MetadataProvider
from bibverify.providers.biorxiv import BiorxivProvider
from bibverify.providers.crossref import CrossrefProvider
from bibverify.providers.dblp import DblpProvider
from bibverify.providers.europe_pmc import EuropePmcProvider
from bibverify.providers.misc import BaseSearchProvider, CoreProvider, GoogleScholarProvider
from bibverify.providers.openalex import OpenAlexProvider
from bibverify.providers.pubmed import PubmedProvider
from bibverify.providers.semantic_scholar import SemanticScholarProvider

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

PROVIDER_TYPES: dict[str, type[MetadataProvider]] = {
    "crossref": CrossrefProvider,
    "openalex": OpenAlexProvider,
    "semantic_scholar": SemanticScholarProvider,
    "pubmed": PubmedProvider,
    "europe_pmc": EuropePmcProvider,
    "core": CoreProvider,
    "dblp": DblpProvider,
    "arxiv": ArxivProvider,
    "biorxiv": BiorxivProvider,
    "base": BaseSearchProvider,
    "google_scholar": GoogleScholarProvider,
}


def build_provider_registry(checker: Any) -> dict[str, MetadataProvider]:
    """Instantiate all query-capable providers for a checker."""
    return {name: provider_type(checker) for name, provider_type in PROVIDER_TYPES.items()}


__all__ = ["PROVIDER_NAMES", "MetadataProvider", "build_provider_registry"]
