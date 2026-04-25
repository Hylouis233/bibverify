import io
import unittest
from contextlib import redirect_stdout

from bib_check import BibTeXChecker


class BibTeXCheckerRankingTests(unittest.TestCase):
    def make_checker(self):
        with redirect_stdout(io.StringIO()):
            return BibTeXChecker("__missing_test_config__.json")

    def test_canonicalize_doi_strips_common_wrappers(self):
        checker = self.make_checker()

        self.assertEqual(
            checker.canonicalize_doi("{https://doi.org/10.1000/XYZ.}"),
            "10.1000/XYZ",
        )
        self.assertEqual(checker.canonicalize_doi("doi: 10.1000/example;"), "10.1000/example")

    def test_identifier_hints_promote_more_specific_sources(self):
        checker = self.make_checker()
        checker.enabled_platforms = [
            "openalex",
            "semantic_scholar",
            "pubmed",
            "crossref",
            "arxiv",
            "dblp",
            "europe_pmc",
        ]

        order = checker._rank_platforms_for_entry(
            "Neural methods for clinical genomics",
            {
                "doi": "10.1000/example",
                "pmid": "12345",
                "archiveprefix": "arXiv",
                "booktitle": "IEEE Conference on Bioinformatics",
            },
        )

        self.assertEqual(order[:5], ["crossref", "arxiv", "pubmed", "europe_pmc", "dblp"])

    def test_unpaywall_is_skipped_as_enrichment_only(self):
        checker = self.make_checker()
        checker.enabled_platforms = ["unpaywall", "crossref"]
        checker.query_crossref_by_doi = lambda doi, title=None: None
        checker.query_crossref = lambda title: ("crossref", {"title": [title]})

        with redirect_stdout(io.StringIO()):
            result = checker.query_multi_platform("A reference title", {"doi": "10.1000/example"})

        self.assertEqual(result[0], "crossref")

    def test_stop_on_first_match_false_preserves_first_match(self):
        checker = self.make_checker()
        checker.config["query_settings"]["stop_on_first_match"] = False
        checker.enabled_platforms = ["crossref", "openalex"]
        checker.query_crossref_by_doi = lambda doi, title=None: None
        checker.query_crossref = lambda title: ("crossref", {"title": [title]})
        checker.query_openalex = lambda title: ("openalex", {"title": title})

        with redirect_stdout(io.StringIO()):
            result = checker.query_multi_platform("A reference title", {})

        self.assertEqual(result[0], "crossref")

    def test_case_protection_does_not_emit_triple_braces(self):
        checker = self.make_checker()
        entry = {
            "ENTRYTYPE": "article",
            "ID": "case2026",
            "title": checker.format_field_value("A Mixed Case Title", protect_case=True),
        }

        bibtex = checker.entry_to_bibtex(entry)

        self.assertIn("title = {{A Mixed Case Title}}", bibtex)
        self.assertNotIn("{{{A Mixed Case Title}}}", bibtex)


if __name__ == "__main__":
    unittest.main()
