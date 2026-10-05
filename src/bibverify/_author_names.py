"""Author-name and text normalization helpers for bibliographic matching."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

_GENERATIONAL_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq"})
# Undotted all-caps trailing blocks that stay PubMed given-initials even though
# they could be read as a short surname (``Smith JR`` / ``Smith SR`` / ``Doe MD``).
_PUBMED_INITIAL_BLOCKS = frozenset({"jr", "sr", "md", "phd", "ii", "iii", "iv", "esq"})
