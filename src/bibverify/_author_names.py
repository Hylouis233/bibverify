"""Author-name and text normalization helpers for bibliographic matching."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

_GENERATIONAL_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq"})


def normalize_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\\[a-zA-Z]+\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"[{}]", "", text)
    text = unicodedata.normalize("NFKC", text).casefold()
    text = (
        text.replace("\N{GREEK SMALL LETTER BETA}", " beta ")
        .replace("\N{GREEK SMALL LETTER ALPHA}", " alpha ")
        .replace("\N{GREEK SMALL LETTER GAMMA}", " gamma ")
    )
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def expand_abbreviated_page_range(text: str) -> str:
    """Expand BibTeX-style abbreviated end pages (``683--97`` → ``683-697``)."""
    normalized = re.sub(r"[-\u2013\u2014]+", "-", text.strip())
    match = re.fullmatch(r"(\d+)-(\d+)", normalized)
    if not match:
        return normalized
    start, end = match.group(1), match.group(2)
    if 0 < len(end) < len(start):
        expanded = start[: -len(end)] + end
        if int(expanded) >= int(start):
            end = expanded
    return f"{start}-{end}"


def normalize_pages(value: Any) -> str:
    # Expand abbreviated end pages before normalize_text strips hyphens.
    dashed = re.sub(r"[-\u2013\u2014]+", "-", str(value or "").strip())
    return normalize_text(expand_abbreviated_page_range(dashed))


def _is_cjk_ideograph_token(token: str) -> bool:
    """True when any character is a CJK ideograph (undotted CJK given names are full names)."""
    for char in token:
        code = ord(char)
        if (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0xF900 <= code <= 0xFAFF
            or 0x20000 <= code <= 0x2A6DF
        ):
            return True
    return False


def _is_initial_letter(token: str) -> bool:
    """Single-letter initial in Latin/Cyrillic/Greek scripts; never a CJK ideograph."""
    return len(token) == 1 and token.isalpha() and not _is_cjk_ideograph_token(token)


def _raw_token_looks_like_initials(token: str) -> bool:
    """Evidence that a *source* token is initials, not a short surname/given name.

    Compact Latin blocks need uppercase or dotted form (``MN``, ``JR``, ``M.N.``).
    Generational spellings such as ``JR`` are valid PubMed given-initials in
    family-first position and must not be rejected by a suffix blacklist.
    Mixed-case short surnames such as ``Li`` / ``Kim`` stay surnames.
    Non-Latin single letters need a trailing period (``И.``); undotted CJK never.
    """
    stripped = token.replace(".", "")
    if not stripped.isalpha() or _is_cjk_ideograph_token(stripped):
        return False
    if len(stripped) == 1:
        return stripped.isascii() or ("." in token)
    if 2 <= len(stripped) <= 4 and stripped.isascii():
        return stripped.isupper() or ("." in token)
    return False


def _expanded_matches_initial(name: str, initial: str) -> bool:
    """Initial letter may expand onto a longer given name (``J`` ≡ ``josé``, ``и`` ≡ ``иван``)."""
    return (
        _is_initial_letter(initial)
        and len(name) > 1
        and name.isalpha()
        and name.startswith(initial)
    )


def _collapse_initials(tokens: list[str]) -> list[str]:
    """Join adjacent single-letter initials so ``P M`` matches ``PM``."""
    collapsed: list[str] = []
    buffer: list[str] = []
    for token in tokens:
        if _is_initial_letter(token):
            buffer.append(token)
            continue
        if buffer:
            collapsed.append("".join(buffer))
            buffer = []
        collapsed.append(token)
    if buffer:
        collapsed.append("".join(buffer))
    return collapsed


def _strip_trailing_generational(tokens: list[str]) -> list[str]:
    if tokens and tokens[-1] in _GENERATIONAL_SUFFIXES:
        return tokens[:-1]
    return tokens


def _split_given_tokens_from_raw(raw_given: str) -> list[str]:
    """Normalize given-name tokens; split uppercase/dotted compact initials into letters."""
    raw_given = raw_given.strip()
    if not raw_given:
        return []
    if _raw_token_looks_like_initials(raw_given) and " " not in raw_given:
        stripped = raw_given.replace(".", "")
        return list(stripped.casefold())
    return _strip_trailing_generational(normalize_text(raw_given).split())


def _split_author_list(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [
        part for part in re.split(r"\s+and\s+|\s*;\s*", text, flags=re.IGNORECASE) if part.strip()
    ]


def _person_name_collapsed(name: str) -> str:
    return " ".join(_collapse_initials(normalize_text(name).split()))


def normalize_person_list(value: Any) -> str:
    """Normalize author/editor lists for equivalence checks."""
    names = _split_author_list(value)
    normalized_names = [collapsed for name in names if (collapsed := _person_name_collapsed(name))]
    return " and ".join(normalized_names)


def _parse_person_name(name: str) -> tuple[str, list[str]]:
    """Split a person into ``(family, given_tokens)`` without collapsing initials."""
    raw = str(name or "").strip()
    if not raw:
        return "", []
    if "," in raw:
        family, given = raw.split(",", 1)
        return normalize_text(family), _split_given_tokens_from_raw(given)
    raw_tokens = re.split(r"\s+", raw)
    tokens = normalize_text(raw).split()
    if not tokens:
        return "", []
    # PubMed-style ``Family I`` / ``Family MN`` / ``Family JR`` (no comma).
    if len(raw_tokens) >= 2 and _raw_token_looks_like_initials(raw_tokens[-1]):
        trailing = raw_tokens[-1]
        stripped = trailing.replace(".", "")
        return " ".join(tokens[:-1]), list(stripped.casefold())
    # Western ``Given Family``
    return tokens[-1], _strip_trailing_generational(tokens[:-1])


def _given_tokens_equivalent(left: list[str], right: list[str]) -> bool:
    """Allow initials to match expanded given names; keep full-name disagreements."""
    left = _strip_trailing_generational(left)
    right = _strip_trailing_generational(right)
    if _collapse_initials(left) == _collapse_initials(right):
        return True
    return _align_given_tokens(left, right)


def _align_given_tokens(left: list[str], right: list[str]) -> bool:
    """Iterative two-pointer alignment for initials (avoids RecursionError)."""
    stack: list[tuple[int, int]] = [(0, 0)]
    seen: set[tuple[int, int]] = set()
    while stack:
        left_index, right_index = stack.pop()
        if (left_index, right_index) in seen:
            continue
        seen.add((left_index, right_index))
        if left_index == len(left) and right_index == len(right):
            return True
        if left_index == len(left) or right_index == len(right):
            continue
        first = left[left_index]
        second = right[right_index]
        if first == second:
            stack.append((left_index + 1, right_index + 1))
        if _expanded_matches_initial(second, first):
            stack.append((left_index + 1, right_index + 1))
        if _expanded_matches_initial(first, second):
            stack.append((left_index + 1, right_index + 1))
    return False


def _persons_equivalent(left: str, right: str) -> bool:
    """Compare one author pair; comma structure is checked per author, not per list."""
    if ("," in left) == ("," in right) and _person_name_collapsed(left) == _person_name_collapsed(
        right
    ):
        return True
    left_family, left_given = _parse_person_name(left)
    right_family, right_given = _parse_person_name(right)
    if left_family != right_family:
        return False
    return _given_tokens_equivalent(left_given, right_given)


def person_lists_equivalent(left: Any, right: Any) -> bool:
    """True when two author/editor lists name the same people under light variants.

    Accepts initials vs expanded given names (``M. N.`` / ``MN`` / ``JR`` ≡ expanded,
    ``W`` ≡ ``William``, ``И.`` ≡ ``Иван``), PubMed-style ``Family I`` forms, and
    punctuation/case variants that keep each author's family/given ordering, but
    still treats distinct expanded given names (including undotted CJK) as different.
    """
    left_names = _split_author_list(left)
    right_names = _split_author_list(right)
    if len(left_names) != len(right_names):
        return False
    if not left_names:
        return True
    return all(
        _persons_equivalent(left_name, right_name)
        for left_name, right_name in zip(left_names, right_names, strict=True)
    )


def _authors(value: Any) -> set[str]:
    text = html.unescape(str(value or ""))
    if not text.strip():
        return set()
    names = re.split(r"\s+and\s+|\s*;\s*", text, flags=re.IGNORECASE)
    normalized: set[str] = set()
    for name in names:
        family, _given = _parse_person_name(name)
        if family:
            normalized.add(family)
    return normalized
