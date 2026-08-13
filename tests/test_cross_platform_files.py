import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from bibverify.checker import BibTeXChecker


def make_checker(tmp_path, *, language="EN", output_settings=None):
    bib = tmp_path / "参考 文献.bib"
    raw = b"@article{demo,\r\n  title={Demo},\r\n  year={2026}\r\n}\r\n"
    bib.write_bytes(raw)
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "language": language,
                "bib_file": bib.name,
                "output_dir": "results",
                "output_settings": {"timestamp_format": "fixed", **(output_settings or {})},
            }
        ),
        encoding="utf-8",
    )
    with redirect_stdout(StringIO()):
        checker = BibTeXChecker(config)
        checker.load_bib_file()
    checker.results = {"verified": [], "updated": [], "not_found": [], "errors": []}
    return checker, raw


def test_backup_is_byte_for_byte_and_output_is_absolute(tmp_path):
    checker, raw = make_checker(tmp_path)

    with redirect_stdout(StringIO()):
        checker.generate_updated_bib()

    backup = Path(checker.last_output_files["backup"])
    assert backup.is_absolute()
    assert backup.read_bytes() == raw


def test_output_switches_are_honored(tmp_path):
    checker, _ = make_checker(
        tmp_path,
        output_settings={"generate_report": False, "generate_backup": False},
    )

    with redirect_stdout(StringIO()):
        assert checker.generate_report() is None
        checker.generate_updated_bib()

    assert checker.last_output_files["report"] is None
    assert checker.last_output_files["backup"] is None
    assert not list((tmp_path / "results").glob("*_backup_*.bib"))


def test_english_report_is_not_hard_coded_chinese(tmp_path):
    checker, _ = make_checker(tmp_path, language="EN")

    with redirect_stdout(StringIO()):
        report = Path(checker.generate_report())

    text = report.read_text(encoding="utf-8")
    assert "BibTeX verification report" in text
    assert "总计检查" not in text


def test_updated_file_contains_changed_and_unchanged_entries(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{changed, title={Old}, year={2020}}\n\n"
        "@article{unchanged, title={Keep me}, year={2021}}\n",
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "bib_file": bib.name,
                "output_settings": {"timestamp_format": "fixed"},
            }
        ),
        encoding="utf-8",
    )
    with redirect_stdout(StringIO()):
        checker = BibTeXChecker(config)
        checker.load_bib_file()
        changed = next(entry for entry in checker.db.entries if entry["ID"] == "changed")
        replacement = dict(changed, title="{New}")
        checker.results = {
            "verified": [],
            "updated": [
                {
                    "key": "changed",
                    "original": changed,
                    "updated": replacement,
                    "differences": {"title": {"original": "Old", "updated": "New"}},
                    "platform": "crossref",
                }
            ],
            "not_found": [],
            "errors": [],
        }
        updated, _ = checker.generate_updated_bib()

    content = Path(updated).read_text(encoding="utf-8")
    assert "@article{changed" in content
    assert "@article{unchanged" in content
    assert "title = {{New}}" in content
    assert "title = {Keep me}" in content or "title = {{Keep me}}" in content
