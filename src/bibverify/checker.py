"""BibTeX verification engine.

This module intentionally preserves the public ``BibTeXChecker`` API while
the command-line and MCP transports live in separate modules.
"""

import re
from copy import deepcopy
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit

import bibtexparser
from bibtexparser.bparser import BibTexParser

from bibverify.bibtex import BibTeXMixin
from bibverify.cache import ResponseCache
from bibverify.config import DEFAULT_CONFIG, deep_merge, load_config
from bibverify.http import ResilientSession
from bibverify.i18n import LanguageSupport
from bibverify.identifiers import extract_identifiers
from bibverify.provider_queries import ProviderQueriesMixin
from bibverify.providers import build_provider_registry
from bibverify.workflow import WorkflowMixin

__all__ = ["BibTeXChecker", "LanguageSupport"]


class BibTeXChecker(ProviderQueriesMixin, BibTeXMixin, WorkflowMixin):
    def __init__(
        self,
        config_file="config.json",
        *,
        overrides=None,
        http_client=None,
        dry_run=False,
        apply_changes=False,
    ):
        self.config_file = Path(config_file).expanduser().resolve(strict=False)
        self.config = self.load_config(config_file, overrides=overrides)
        self.bib_file = self.config.get("bib_file", "references.bib")
        self.output_dir = Path(self.config["output_dir"])
        self.file_encoding = "utf-8"
        self.output_newline = "\n"
        self.db = None
        self.results = self._empty_results()
        self.last_output_files = {}
        self.dry_run = bool(dry_run)
        self.apply_changes = bool(apply_changes)
        if self.dry_run and self.apply_changes:
            raise ValueError("dry_run and apply_changes are mutually exclusive.")
        self.user_email = self.config.get("user_info", {}).get("email", "research@example.com")
        self.app_name = self.config.get("user_info", {}).get("app_name", "Bibverify")
        self.enabled_platforms = self._get_enabled_platforms()

        language = self.config.get("language", "CN")
        self.lang = LanguageSupport(language)

        query = self.config.get("query_settings", {})
        response_cache = None
        if query.get("cache_enabled", True) and not self.dry_run:
            response_cache = ResponseCache(
                query["cache_path"],
                ttl_seconds=float(query.get("cache_ttl_hours", 168)) * 3600,
            )
        self.http = http_client or ResilientSession(
            timeout=(
                float(query.get("connect_timeout", 3.05)),
                float(query.get("read_timeout", query.get("timeout", 20))),
            ),
            max_retries=int(query.get("max_retries", 3)),
            backoff_factor=float(query.get("backoff_factor", 0.5)),
            min_interval=float(query.get("delay_between_requests", 0.5)),
            user_agent=f"{self.app_name}/0.3 (mailto:{self.user_email})",
            cache=response_cache,
        )
        self.provider_registry = build_provider_registry(self)

    @staticmethod
    def _empty_results():
        return {
            "verified": [],
            "updated": [],
            "ambiguous": [],
            "not_found": [],
            "source_unavailable": [],
            "identifier_conflict": [],
            "invalid_input": [],
            "errors": [],
        }

    @staticmethod
    def extract_identifiers(entry):
        return extract_identifiers(entry)

    def load_config(self, config_file, *, overrides=None):
        config, resolved_path = load_config(config_file, overrides=overrides)
        self.config_file = resolved_path
        return config

    def _merge_config(self, default_config, user_config):
        return deep_merge(default_config, user_config)

    def _get_default_config(self):
        return deepcopy(DEFAULT_CONFIG)

    def _get_enabled_platforms(self):
        platforms = self.config.get("platforms", {})
        enabled = []
        for name, settings in platforms.items():
            if settings.get("enabled", False):
                enabled.append((name, settings.get("priority", 999)))
        enabled.sort(key=lambda x: x[1])
        return [name for name, _ in enabled]

    def _has_arxiv_identifier(self, entry):
        if not entry:
            return False
        archive_prefix = str(entry.get("archiveprefix", entry.get("archivePrefix", ""))).lower()
        eprint = str(entry.get("eprint", ""))
        url = str(entry.get("url", ""))
        doi = self.canonicalize_doi(entry.get("doi", ""))
        return (
            archive_prefix == "arxiv"
            or self._is_arxiv_url(url)
            or bool(re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", eprint))
            or doi.lower().startswith("10.48550/arxiv.")
        )

    @staticmethod
    def _is_arxiv_url(value):
        raw_url = str(value).strip()
        if not raw_url:
            return False

        parsed = urlsplit(
            raw_url if "://" in raw_url or raw_url.startswith("//") else f"//{raw_url}"
        )
        hostname = (parsed.hostname or "").lower().rstrip(".")
        return hostname == "arxiv.org" or hostname.endswith(".arxiv.org")

    def _looks_biomedical(self, entry, title):
        if not entry:
            return False
        if entry.get("pmid") or entry.get("pmcid"):
            return True
        text = " ".join(
            str(entry.get(field, "")) for field in ["journal", "booktitle", "publisher", "keywords"]
        )
        text = f"{text} {title}".lower()
        biomedical_terms = [
            "pubmed",
            "pmc",
            "medline",
            "medicine",
            "medical",
            "biomed",
            "biology",
            "bioinformatics",
            "genome",
            "clinical",
            "epidemiology",
            "biorxiv",
            "medrxiv",
        ]
        return any(term in text for term in biomedical_terms)

    def _looks_computer_science(self, entry, title):
        if not entry:
            return False
        text = " ".join(
            str(entry.get(field, "")) for field in ["journal", "booktitle", "publisher", "keywords"]
        )
        text = f"{text} {title}".lower()
        cs_terms = [
            "acm",
            "ieee",
            "computer",
            "computing",
            "software",
            "algorithm",
            "machine learning",
            "artificial intelligence",
            "neural",
            "conference on",
            "symposium on",
        ]
        return any(term in text for term in cs_terms)

    def _rank_platforms_for_entry(self, title, entry=None):
        platforms = list(self.enabled_platforms)
        if not entry:
            return platforms

        boosts = {}
        if entry.get("doi"):
            boosts["crossref"] = -100
        if entry.get("pmid") or entry.get("pmcid") or self._looks_biomedical(entry, title):
            boosts["pubmed"] = min(boosts.get("pubmed", 0), -80)
            boosts["europe_pmc"] = min(boosts.get("europe_pmc", 0), -70)
            boosts["biorxiv"] = min(boosts.get("biorxiv", 0), -30)
        if self._has_arxiv_identifier(entry):
            boosts["arxiv"] = min(boosts.get("arxiv", 0), -90)
        if self._looks_computer_science(entry, title):
            boosts["dblp"] = min(boosts.get("dblp", 0), -60)

        original_position = {platform: idx for idx, platform in enumerate(platforms)}
        return sorted(
            platforms,
            key=lambda platform: (boosts.get(platform, 0), original_position[platform]),
        )

    def load_bib_file(self):
        requested_encoding = str(self.config.get("encoding", "auto")).strip().lower()
        encodings = (
            ["utf-8-sig", "utf-8", "gb18030"]
            if requested_encoding == "auto"
            else [requested_encoding]
        )
        success = False

        raw = Path(self.bib_file).read_bytes()
        self.output_newline = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") / 2 else "\n"

        for encoding in encodings:
            try:
                with open(self.bib_file, encoding=encoding, newline="") as bibfile:
                    parser = BibTexParser(common_strings=True)
                    parser.ignore_nonstandard_types = False
                    self.db = bibtexparser.load(bibfile, parser)
                success = True
                self.file_encoding = encoding
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Warning: Failed to load with encoding {encoding}: {e}")
                continue

        if not success:
            raise ValueError(
                f"Unable to decode {self.bib_file}. Tried: {', '.join(encodings)}. "
                "Set 'encoding' explicitly in the config if needed."
            )

        print(self.lang.get_text("loaded_entries", count=len(self.db.entries)))

    def clean_title(self, title):
        title = re.sub(r"\{|\}", "", title)
        title = re.sub(r"\s+", " ", title)
        return title.strip()

    def normalize_title(self, title):
        title = self.clean_title(title)
        title = title.lower()
        title = re.sub(r"\s+", " ", title)
        return title.strip()

    def normalize_for_comparison(self, title):
        title = self.normalize_title(title)
        title = re.sub(r"[^\w\s]", "", title)
        title = re.sub(r"\s+", " ", title)
        return title.strip()

    def is_title_match(self, original_title, candidate_title):
        norm_original = self.normalize_for_comparison(original_title)
        norm_candidate = self.normalize_for_comparison(candidate_title)
        if not norm_original or not norm_candidate:
            return False

        if norm_original == norm_candidate:
            return True

        shorter, longer = sorted((norm_original, norm_candidate), key=len)
        containment = len(shorter) / len(longer) if shorter in longer else 0.0
        sequence = SequenceMatcher(None, norm_original, norm_candidate).ratio()
        original_tokens = set(norm_original.split())
        candidate_tokens = set(norm_candidate.split())
        union = original_tokens | candidate_tokens
        token_overlap = len(original_tokens & candidate_tokens) / len(union) if union else 0.0
        score = max(sequence, containment * 0.95, token_overlap)
        threshold = float(self.config.get("query_settings", {}).get("title_match_threshold", 0.86))
        return score >= threshold

    def canonicalize_doi(self, doi):
        # Preserve the user's DOI case for the public v0.2 API. Internal
        # identifier comparisons use ``identifiers.canonicalize_doi`` and are
        # deliberately case-insensitive.
        if not doi:
            return ""
        value = self.clean_title(str(doi)).strip().strip("{}").strip()
        value = re.sub(r"^doi\s*:\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
        return value.strip().strip(".,;")
