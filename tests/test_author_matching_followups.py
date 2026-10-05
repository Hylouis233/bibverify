"""Regressions for Codex author-matching follow-ups on PR #48 / #49."""

from __future__ import annotations

from bibverify.matching import (
    assess_match,
    expand_abbreviated_page_range,
    person_lists_equivalent,
)
from bibverify.merge import merge_entries
from bibverify.models import QueryStatus
