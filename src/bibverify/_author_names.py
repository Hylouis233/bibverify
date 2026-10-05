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


def _raw_token_looks_like_initials(token: str, *, comma_given: bool = False) -> bool:
    """Initials vs short names; comma_given keeps vowel-bearing ``BO`` as a full given."""
    stripped = token.replace(".", "")
    if not stripped.isalpha() or _is_cjk_ideograph_token(stripped):
        return False
    if len(stripped) == 1:
        return stripped.isascii() or ("." in token)
    if 2 <= len(stripped) <= 4 and stripped.isascii():
        if "." in token:
            return True
        folded = stripped.casefold()
        if folded in _PUBMED_INITIAL_BLOCKS:
            return True
        if len(stripped) != 2 or not stripped.isupper():
            return False
        if comma_given:
            # ``Li, BO`` is a short given name; ``Meyer, MN`` stays compact initials.
            return not any(char in "AEIOU" for char in stripped)
        # Family-first / general: ``MN`` / ``AM`` / ``JR`` packs are compact initials.
        return True
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


def _split_generational_suffix(tokens: list[str]) -> tuple[list[str], str | None]:
    """Split trailing generational/degree suffix; sole ``v`` stays a middle initial."""
    if len(tokens) < 2 or tokens[-1] not in _GENERATIONAL_SUFFIXES:
        return tokens, None
    if tokens[-1] == "v":
        return tokens, None
    return tokens[:-1], tokens[-1]


def _strip_trailing_generational(tokens: list[str]) -> list[str]:
    """Drop a trailing generational/degree suffix only in true suffix position."""
    core, _suffix = _split_generational_suffix(tokens)
    return core


def _split_given_tokens_from_raw(raw_given: str) -> list[str]:
    """Normalize given-name tokens; keep generational suffixes for equivalence checks."""
    raw_given = raw_given.strip()
    if not raw_given:
        return []
    if _raw_token_looks_like_initials(raw_given, comma_given=True) and " " not in raw_given:
        stripped = raw_given.replace(".", "")
        return list(stripped.casefold())
    # Keep Jr/Sr/II/... so conflicting suffixes are not erased before compare.
    return normalize_text(raw_given).split()


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
    return _parse_person_name_candidates(name)[0]


def _looks_like_western_given(raw_token: str) -> bool:
    """Mixed-case, undotted, multi-letter token such as ``Ada`` (not ``ADA`` / ``A.``)."""
    return (
        len(raw_token) >= 2
        and raw_token.isalpha()
        and not raw_token.isupper()
        and not _raw_token_looks_like_initials(raw_token)
    )


def _looks_like_undotted_allcaps_full_name(raw_token: str) -> bool:
    """Undotted all-caps full given (``ADA``), not compact initials (``MN`` / ``A.``)."""
    if "." in raw_token:
        return False
    return (
        len(raw_token) >= 3
        and raw_token.isascii()
        and raw_token.isalpha()
        and raw_token.isupper()
        and not _raw_token_looks_like_initials(raw_token)
    )


def _looks_like_leading_given_or_initial(raw_token: str) -> bool:
    """Leading evidence for ``Given… FAMILY`` / ``ADA LI`` / ``A. B. NG`` before surname."""
    return (
        _looks_like_western_given(raw_token)
        or _raw_token_looks_like_initials(raw_token)
        or _looks_like_undotted_allcaps_full_name(raw_token)
    )


def _is_allcaps_short_surname(raw_tokens: list[str]) -> bool:
    """Trailing all-caps block after given/initial evidence reads as a surname."""
    if len(raw_tokens) < 2:
        return False
    trailing = raw_tokens[-1]
    if not (
        2 <= len(trailing) <= 4 and trailing.isascii() and trailing.isalpha() and trailing.isupper()
    ):
        return False
    if trailing.casefold() in _PUBMED_INITIAL_BLOCKS:
        return False
    return all(_looks_like_leading_given_or_initial(token) for token in raw_tokens[:-1])


def _pubmed_family_first_parse(raw_tokens: list[str]) -> tuple[str, list[str]] | None:
    """Family before trailing initials run (``Smith M.N.`` → family smith, given m+n)."""
    if len(raw_tokens) < 2:
        return None
    index = len(raw_tokens)
    while index > 1 and _raw_token_looks_like_initials(raw_tokens[index - 1]):
        index -= 1
    if index >= len(raw_tokens):
        return None
    family = normalize_text(" ".join(raw_tokens[:index]))
    given: list[str] = []
    for token in raw_tokens[index:]:
        stripped = token.replace(".", "")
        if stripped:
            given.extend(list(stripped.casefold()))
    if not family or not given:
        return None
    return family, given


def _parse_person_name_candidates(name: str) -> list[tuple[str, list[str]]]:
    """Plausible ``(family, given_tokens)`` parses, most likely first."""
    raw = str(name or "").strip()
    if not raw:
        return [("", [])]
    if "," in raw:
        parts = [part.strip() for part in raw.split(",")]
        # BibTeX ``von Last, Jr, First`` (two commas): middle segment is the suffix.
        if len(parts) >= 3:
            middle = normalize_text(parts[1])
            if middle and middle != "v" and middle in _GENERATIONAL_SUFFIXES:
                family = normalize_text(parts[0])
                given = _split_given_tokens_from_raw(",".join(parts[2:]))
                return [(family, [*given, middle])]
        family, given = parts[0], ",".join(parts[1:])
        return [(normalize_text(family), _split_given_tokens_from_raw(given))]
    raw_tokens = re.split(r"\s+", raw)
    tokens = normalize_text(raw).split()
    if not tokens:
        return [("", [])]
    # Prefer family = last non-suffix token; keep Jr/Sr on the given side for compare.
    core_tokens, gen_suffix = _split_generational_suffix(tokens)
    if not core_tokens:
        return [("", [])]
    given_core = list(core_tokens[:-1])
    if gen_suffix is not None:
        given_core.append(gen_suffix)
    western = (core_tokens[-1], given_core)
    # PubMed-style ``Family I`` / ``Family MN`` / ``Family M.N.`` / ``Family M. N.``.
    if len(raw_tokens) >= 2 and _raw_token_looks_like_initials(raw_tokens[-1]):
        pubmed = _pubmed_family_first_parse(raw_tokens)
        if pubmed is not None:
            if _is_allcaps_short_surname(raw_tokens):
                return [western, pubmed]
            return [pubmed]
    # Western ``Given Family``
    return [western]


def _given_tokens_equivalent(left: list[str], right: list[str]) -> bool:
    """Initials may expand; optional one-sided suffix/middle; conflicting suffixes differ."""
    left_core, left_suffix = _split_generational_suffix(left)
    right_core, right_suffix = _split_generational_suffix(right)
    if left_suffix is not None and right_suffix is not None and left_suffix != right_suffix:
        return False
    if _collapse_initials(left_core) == _collapse_initials(right_core):
        return True
    return _align_given_tokens(left_core, right_core)


def _align_given_tokens(left: list[str], right: list[str]) -> bool:
    """Iterative given-token alignment; optional one-sided middles after a shared match."""
    stack: list[tuple[int, int]] = [(0, 0)]
    seen: set[tuple[int, int]] = set()
    while stack:
        left_index, right_index = stack.pop()
        if (left_index, right_index) in seen:
            continue
        seen.add((left_index, right_index))
        if left_index == len(left) and right_index == len(right):
            return True
        # Optional middle names/initials on one side only after a shared match
        # (``John`` ≡ ``John A``), but not empty ≡ non-empty (``Rahman`` ≢ ``Md Rahman``).
        if left_index == len(left) or right_index == len(right):
            if left_index > 0 or right_index > 0:
                return True
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
    left_has_comma = "," in left
    right_has_comma = "," in right
    if left_has_comma == right_has_comma and _person_name_collapsed(left) == _person_name_collapsed(
        right
    ):
        if not left_has_comma:
            return True
        # Both have commas: collapsed text alone can hide different family/given cuts
        # (``Smith A, B`` vs ``Smith, A B`` both collapse to ``smith ab``).
        left_family = normalize_text(left.split(",", 1)[0])
        right_family = normalize_text(right.split(",", 1)[0])
        if left_family == right_family:
            return True
    return any(
        left_family == right_family and _given_tokens_equivalent(left_given, right_given)
        for left_family, left_given in _parse_person_name_candidates(left)
        for right_family, right_given in _parse_person_name_candidates(right)
    )


def person_lists_equivalent(left: Any, right: Any) -> bool:
    """True when two author/editor lists name the same people under light variants."""
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
    """Preferred family tokens only (first candidate parse per author)."""
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


def _maximum_person_matches(left_names: list[str], right_names: list[str]) -> int:
    """Maximum bipartite matching under ``_persons_equivalent`` (order-independent)."""
    adjacency = [
        [
            right_index
            for right_index, right_name in enumerate(right_names)
            if _persons_equivalent(left_name, right_name)
        ]
        for left_name in left_names
    ]
    match_to_left = [-1] * len(right_names)

    def _augment(start_left: int) -> bool:
        """Iterative DFS augmenting path (avoids RecursionError on large author lists)."""
        seen = [False] * len(right_names)
        # Stack frames: (left_index, next_neighbor_offset); path holds chosen edges.
        stack: list[tuple[int, int]] = [(start_left, 0)]
        path: list[tuple[int, int]] = []
        while stack:
            left_index, offset = stack[-1]
            neighbors = adjacency[left_index]
            if offset < len(neighbors):
                stack[-1] = (left_index, offset + 1)
                right_index = neighbors[offset]
                if seen[right_index]:
                    continue
                seen[right_index] = True
                matched = match_to_left[right_index]
                path.append((left_index, right_index))
                if matched == -1:
                    for path_left, path_right in path:
                        match_to_left[path_right] = path_left
                    return True
                stack.append((matched, 0))
            else:
                stack.pop()
                if path:
                    path.pop()
        return False

    hits = 0
    for left_index in range(len(left_names)):
        if _augment(left_index):
            hits += 1
    return hits


def author_lists_overlap(left: Any, right: Any) -> float | None:
    """Person-compatible author overlap via bipartite matching; union denominator."""
    left_names = _split_author_list(left)
    right_names = _split_author_list(right)
    if not left_names or not right_names:
        return None
    hits = _maximum_person_matches(left_names, right_names)
    # Union denominator so partial overlap is not overstated (1 of 2 vs 1 of 2 → 1/3).
    return hits / (len(left_names) + len(right_names) - hits)
