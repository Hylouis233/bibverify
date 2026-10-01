"""Regression tests for preserving BibTeX content while applying metadata updates."""

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import bibtexparser
import pytest

from bibverify.bibtex import BibTeXMixin
from bibverify.checker import BibTeXChecker


@pytest.mark.parametrize(
    "title",
    [
        "{GPU} and {CPU}",
        r"Nested {\textit{Mixed}} Title",
        r"An escaped \{brace\} and {GPU}",
    ],
)
def test_case_protection_preserves_internal_groups(title):
    helper = BibTeXMixin()
    protected = helper.format_field_value(title)
    assert protected == "{" + title + "}"
    serialized = helper.entry_to_bibtex({"ID": "demo", "ENTRYTYPE": "article", "title": protected})
    parsed = bibtexparser.loads(serialized)
    assert len(parsed.entries) == 1
    assert parsed.entries[0]["title"] == protected


@pytest.mark.parametrize("title", ["Title", "{Title}", "{{Title}}"])
def test_case_protection_deduplicates_only_whole_value_wrappers(title):
    helper = BibTeXMixin()
    assert helper.format_field_value(title) == "{Title}"
    assert helper.format_field_value(title, protect_case=False) == "Title"


def test_apply_preserves_preamble_comments_and_string_definitions(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        '@preamble{"\\newcommand{\\noop}[1]{}"}\n'
        "@comment{Keep this bibliography annotation}\n"
        '@string{journalname = "Example Journal"}\n'
        "@article{demo, title={Old}, journal=journalname, year={2026}}\n",
        encoding="utf-8",
    )
    original_bytes = bib.read_bytes()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"bib_file": bib.name}), encoding="utf-8")
    with redirect_stdout(StringIO()):
        checker = BibTeXChecker(config, apply_changes=True)
        checker.load_bib_file()
        original = checker.db.entries[0]
        checker.results["updated"].append(
            {
                "key": "demo",
                "updated": dict(original, title="{New}"),
                "differences": {"title": {"original": "Old", "updated": "{New}"}},
            }
        )
        before = checker.db
        merged = checker._merged_database()
        assert merged.preambles == before.preambles
        assert merged.comments == before.comments
        assert merged.strings == before.strings
        checker.generate_updated_bib()
    parsed = bibtexparser.loads(bib.read_text(encoding=checker.file_encoding))
    assert parsed.preambles == before.preambles
    assert parsed.comments == before.comments
    assert parsed.strings == before.strings
    assert parsed.entries[0]["title"] == "{New}"
    assert before.entries[0]["title"] == "Old"
    assert Path(checker.last_output_files["backup"]).read_bytes() == original_bytes
