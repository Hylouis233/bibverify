"""Codex follow-up patches for author matching (PR #48 review)."""

from __future__ import annotations

import re
from typing import Any, Callable

# Bound by apply() from the matching module to avoid circular imports at load time.
normalize_text: Callable[[Any], str]


_GENERATIONAL_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq"})


def _is_latin_initial(token: str) -> bool:
    """True for a single Latin letter used as an initial (not a CJK given name)."""
    return len(token) == 1 and token.isascii() and token.isalpha()


def _looks_like_compact_latin_initials(token: str) -> bool:
    """True for compact Latin initial blocks such as ``mn`` / ``pm`` (from ``M.N.``)."""
    return (
        2 <= len(token) <= 4
        and token.isascii()
        and token.isalpha()
        and token not in _GENERATIONAL_SUFFIXES
    )


def _is_latin_initials_token(token: str) -> bool:
    return _is_latin_initial(token) or _looks_like_compact_latin_initials(token)


def _expanded_matches_latin_initial(name: str, initial: str) -> bool:
    return (
        _is_latin_initial(initial)
        and len(name) > 1
        and name.isascii()
        and name.isalpha()
        and name.startswith(initial)
    )


def _collapse_initials(tokens: list[str]) -> list[str]:
    """Join adjacent single-letter tokens so ``P M`` matches ``PM``."""
    collapsed: list[str] = []
    buffer: list[str] = []
    for token in tokens:
        if _is_latin_initial(token):
            buffer.append(token)
            continue
        if buffer:
            collapsed.append("".join(buffer))
            buffer = []
        collapsed.append(token)
    if buffer:
        collapsed.append("".join(buffer))
    return collapsed


def normalize_person_list(value: Any) -> str:
    """Normalize author/editor lists for equivalence checks."""
    text = str(value or "").strip()
    if not text:
        return ""
    names = re.split(r"\s+and\s+|\s*;\s*", text, flags=re.IGNORECASE)
    normalized_names: list[str] = []
    for name in names:
        tokens = _collapse_initials(normalize_text(name).split())
        if tokens:
            normalized_names.append(" ".join(tokens))
    return " and ".join(normalized_names)


def _parse_person_name(name: str) -> tuple[str, list[str]]:
    """Split a person into ``(family, given_tokens)`` without collapsing initials."""
    raw = str(name or "").strip()
    if not raw:
        return "", []
    if "," in raw:
        family, given = raw.split(",", 1)
        family_key = normalize_text(family)
        given_tokens = normalize_text(given).split()
        return family_key, given_tokens
    tokens = normalize_text(raw).split()
    if not tokens:
        return "", []
    # PubMed-style ``Family I`` / ``Family IJ`` (no comma): trailing Latin initials
    # are given-name initials, not a one-letter surname.
    if len(tokens) >= 2 and _is_latin_initials_token(tokens[-1]):
        trailing = tokens[-1]
        given = list(trailing) if _looks_like_compact_latin_initials(trailing) else [trailing]
        return " ".join(tokens[:-1]), given
    # Western ``Given Family``
    return tokens[-1], tokens[:-1]


def _consume_compact_latin_initials(compact: str, tokens: list[str], start: int) -> int | None:
    """Match each character of a compact initial block against ``tokens[start:]``."""
    index = start
    for char in compact:
        if index >= len(tokens):
            return None
        token = tokens[index]
        if token == char or _expanded_matches_latin_initial(token, char):
            index += 1
            continue
        return None
    return index


def _given_tokens_equivalent(left: list[str], right: list[str]) -> bool:
    """Allow Latin initials to match expanded given names; keep full-name disagreements."""
    if _collapse_initials(left) == _collapse_initials(right):
        return True
    return _align_given_tokens(left, right)


def _align_given_tokens(left: list[str], right: list[str]) -> bool:
    """Two-pointer alignment for Latin initials and compact blocks such as ``mn``."""

    def recurse(left_index: int, right_index: int) -> bool:
        if left_index == len(left) and right_index == len(right):
            return True
        if left_index == len(left) or right_index == len(right):
            return False
        first = left[left_index]
        second = right[right_index]
        if first == second and recurse(left_index + 1, right_index + 1):
            return True
        if _expanded_matches_latin_initial(second, first) and recurse(
            left_index + 1, right_index + 1
        ):
            return True
        if _expanded_matches_latin_initial(first, second) and recurse(
            left_index + 1, right_index + 1
        ):
            return True
        if _looks_like_compact_latin_initials(first):
            consumed = _consume_compact_latin_initials(first, right, right_index)
            if consumed is not None and recurse(left_index + 1, consumed):
                return True
        if _looks_like_compact_latin_initials(second):
            consumed = _consume_compact_latin_initials(second, left, left_index)
            if consumed is not None and recurse(consumed, right_index + 1):
                return True
        return False

    return recurse(0, 0)


def person_lists_equivalent(left: Any, right: Any) -> bool:
    """True when two author/editor lists name the same people under light variants.

    Accepts initials vs expanded given names (``M. N.`` / ``MN`` ≡ ``Michelle N.``,
    ``W`` ≡ ``William``), PubMed-style ``Family I`` forms, and the existing
    punctuation/case/collapse variants, but still treats distinct expanded given
    names (including single-character CJK names) as different.
    """
    # Preserve pre-#48 equality for punctuation / ordering variants such as
    # ``Lovelace, A.`` vs PubMed ``Lovelace A``.
    if normalize_person_list(left) == normalize_person_list(right):
        return True
    left_names = [
        part
        for part in re.split(r"\s+and\s+|\s*;\s*", str(left or "").strip(), flags=re.IGNORECASE)
        if part.strip()
    ]
    right_names = [
        part
        for part in re.split(r"\s+and\s+|\s*;\s*", str(right or "").strip(), flags=re.IGNORECASE)
        if part.strip()
    ]
    if len(left_names) != len(right_names):
        return False
    if not left_names and not right_names:
        return True
    for left_name, right_name in zip(left_names, right_names, strict=True):
        left_family, left_given = _parse_person_name(left_name)
        right_family, right_given = _parse_person_name(right_name)
        if left_family != right_family:
            return False
        if not _given_tokens_equivalent(left_given, right_given):
            return False
    return True


def apply(namespace: dict) -> None:
    """Replace person-matching helpers on the matching module namespace."""
    global normalize_text
    normalize_text = namespace["normalize_text"]
    # Rebind helpers that closed over normalize_text at definition time — they look up
    # normalize_text as a global of THIS module, so updating the global is enough.
    namespace["_GENERATIONAL_SUFFIXES"] = _GENERATIONAL_SUFFIXES
    namespace["_is_latin_initial"] = _is_latin_initial
    namespace["_looks_like_compact_latin_initials"] = _looks_like_compact_latin_initials
    namespace["_is_latin_initials_token"] = _is_latin_initials_token
    namespace["_expanded_matches_latin_initial"] = _expanded_matches_latin_initial
    namespace["_collapse_initials"] = _collapse_initials
    namespace["normalize_person_list"] = normalize_person_list
    namespace["_parse_person_name"] = _parse_person_name
    namespace["_consume_compact_latin_initials"] = _consume_compact_latin_initials
    namespace["_given_tokens_equivalent"] = _given_tokens_equivalent
    namespace["_align_given_tokens"] = _align_given_tokens
    namespace["person_lists_equivalent"] = person_lists_equivalent
