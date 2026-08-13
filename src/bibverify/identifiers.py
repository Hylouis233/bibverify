"""Extraction and canonicalization of scholarly identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
ARXIV_PATTERN = re.compile(
    r"(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z.-]+/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)


def _plain(value: Any) -> str:
    return re.sub(r"[{}]", "", str(value or "")).strip()


def canonicalize_doi(value: Any) -> str:
    """Return a DOI without resolver/prefix wrappers, lower-cased for comparison."""
    text = _plain(value)
    text = re.sub(r"^doi\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
    match = DOI_PATTERN.search(text)
    return (match.group(0) if match else text).rstrip(".,; ").lower()


def canonicalize_pmid(value: Any) -> str:
    text = _plain(value)
    text = re.sub(r"^pmid\s*:\s*", "", text, flags=re.IGNORECASE)
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def canonicalize_pmcid(value: Any) -> str:
    text = _plain(value).upper()
    match = re.search(r"PMC\d+", text)
    return match.group(0) if match else ""


def canonicalize_arxiv(value: Any) -> str:
    text = _plain(value).replace(".pdf", "")
    match = ARXIV_PATTERN.search(text)
    if not match:
        return ""
    return re.sub(r"v\d+$", "", match.group(1), flags=re.IGNORECASE).lower()


@dataclass(frozen=True, slots=True)
class Identifiers:
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    arxiv: str = ""

    @property
    def any(self) -> bool:
        return any((self.doi, self.pmid, self.pmcid, self.arxiv))

    def as_dict(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "doi": self.doi,
                "pmid": self.pmid,
                "pmcid": self.pmcid,
                "arxiv": self.arxiv,
            }.items()
            if value
        }


def extract_identifiers(entry: dict[str, Any] | None) -> Identifiers:
    entry = entry or {}
    doi = canonicalize_doi(entry.get("doi"))
    pmid = canonicalize_pmid(entry.get("pmid"))
    pmcid = canonicalize_pmcid(entry.get("pmcid"))
    arxiv = canonicalize_arxiv(entry.get("eprint"))

    url = _plain(entry.get("url"))
    note = _plain(entry.get("note"))
    howpublished = _plain(entry.get("howpublished"))
    haystack = " ".join((url, note, howpublished))
    if not doi:
        match = DOI_PATTERN.search(haystack)
        doi = canonicalize_doi(match.group(0)) if match else ""
    if not pmid:
        match = re.search(r"(?:pubmed\.ncbi\.nlm\.nih\.gov/|PMID\s*:?\s*)(\d+)", haystack, re.I)
        pmid = match.group(1) if match else ""
    if not pmcid:
        pmcid = canonicalize_pmcid(haystack)
    if not arxiv:
        arxiv = canonicalize_arxiv(haystack)

    archive_prefix = _plain(entry.get("archiveprefix", entry.get("archivePrefix"))).lower()
    if archive_prefix == "arxiv" and not arxiv:
        arxiv = canonicalize_arxiv(entry.get("eprint"))
    if doi.startswith("10.48550/arxiv.") and not arxiv:
        arxiv = canonicalize_arxiv(doi.removeprefix("10.48550/arxiv."))
    return Identifiers(doi=doi, pmid=pmid, pmcid=pmcid, arxiv=arxiv)
