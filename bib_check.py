"""Compatibility import for Bibverify 0.2 users.

New code should import :class:`bibverify.checker.BibTeXChecker` instead.
"""

from bibverify.checker import BibTeXChecker, LanguageSupport

__all__ = ["BibTeXChecker", "LanguageSupport", "main"]


def main(argv=None):
    """Delegate the legacy script entry point to the modern CLI."""
    from bibverify.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
