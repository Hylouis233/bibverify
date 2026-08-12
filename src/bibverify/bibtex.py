"""BibTeX normalization and metadata conversion helpers."""

from __future__ import annotations

import html
import re

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter


class BibTeXMixin:
    def format_field_value(self, value, protect_case=True):
        if value is None:
            return ""
        value = str(value).strip()
        # 解码 HTML 实体 (如 &amp; -> &)
        value = html.unescape(value)

        if not value:
            return ""
        value = re.sub(r"\{+", "{", value)
        value = re.sub(r"\}+", "}", value)
        value = value.strip("{}")

        if protect_case:
            return "{" + value + "}"
        return value

    def clean_entry(self, entry):
        """Remove empty and None values from an entry."""
        cleaned = {}
        for key, value in entry.items():
            if value is not None and str(value).strip():
                cleaned[key] = str(value).strip()
        return cleaned

    def clean_entry_for_writing(self, entry):
        """Prepare an entry for BibTeX output with string-only fields."""
        cleaned = {}
        for key, value in entry.items():
            if value is None:
                # Omit None values from serialized output.
                continue
            elif isinstance(value, str):
                # Strip leading and trailing whitespace from strings.
                cleaned_value = value.strip()
                if cleaned_value:  # 只添加非空字符串
                    cleaned[key] = cleaned_value
            else:
                # Convert remaining scalar types to strings.
                cleaned_value = str(value).strip()
                if cleaned_value:  # 只添加非空字符串
                    cleaned[key] = cleaned_value
        return cleaned

    def semantic_scholar_to_bibtex(self, ss_data, original_key):
        entry = {"ID": original_key}

        pub_types = ss_data.get("publicationTypes", [])
        if "JournalArticle" in pub_types:
            entry["ENTRYTYPE"] = "article"
        elif "Conference" in pub_types:
            entry["ENTRYTYPE"] = "inproceedings"
        else:
            entry["ENTRYTYPE"] = "article"

        if ss_data.get("title"):
            entry["title"] = self.format_field_value(ss_data["title"], protect_case=True)

        if ss_data.get("authors"):
            authors = [
                author.get("name", "") for author in ss_data["authors"] if author.get("name")
            ]
            if authors:
                entry["author"] = " and ".join(authors)

        if ss_data.get("year"):
            entry["year"] = str(ss_data["year"])

        if ss_data.get("venue"):
            if entry["ENTRYTYPE"] == "article":
                entry["journal"] = self.format_field_value(ss_data["venue"], protect_case=True)
            elif entry["ENTRYTYPE"] == "inproceedings":
                entry["booktitle"] = self.format_field_value(ss_data["venue"], protect_case=True)

        if "journal" in ss_data and ss_data["journal"] and "name" in ss_data["journal"]:
            entry["journal"] = self.format_field_value(
                ss_data["journal"]["name"], protect_case=True
            )

        if ss_data.get("doi"):
            entry["doi"] = ss_data["doi"]

        if "externalIds" in ss_data:
            ext_ids = ss_data["externalIds"]
            if "ArXiv" in ext_ids:
                entry["eprint"] = ext_ids["ArXiv"]
                entry["archiveprefix"] = "arXiv"

        return self.clean_entry(entry)

    def dblp_to_bibtex(self, dblp_data, original_key):
        entry = {"ID": original_key}

        entry_type = dblp_data.get("type", "article")
        type_mapping = {
            "Conference and Workshop Papers": "inproceedings",
            "Journal Articles": "article",
            "Informal Publications": "article",
            "Parts in Books or Collections": "incollection",
        }
        entry["ENTRYTYPE"] = type_mapping.get(entry_type, "article")

        if dblp_data.get("title"):
            entry["title"] = self.format_field_value(dblp_data["title"], protect_case=True)

        if "authors" in dblp_data:
            authors_data = dblp_data["authors"].get("author", [])
            if not isinstance(authors_data, list):
                authors_data = [authors_data]
            authors = [a.get("text", "") for a in authors_data if a.get("text")]
            if authors:
                entry["author"] = " and ".join(authors)

        if "year" in dblp_data:
            entry["year"] = str(dblp_data["year"])

        if dblp_data.get("venue"):
            if entry["ENTRYTYPE"] == "article":
                entry["journal"] = self.format_field_value(dblp_data["venue"], protect_case=True)
            elif entry["ENTRYTYPE"] == "inproceedings":
                entry["booktitle"] = self.format_field_value(dblp_data["venue"], protect_case=True)

        if "volume" in dblp_data:
            entry["volume"] = str(dblp_data["volume"])

        if "pages" in dblp_data:
            entry["pages"] = dblp_data["pages"].replace("-", "--")

        if "doi" in dblp_data:
            entry["doi"] = dblp_data["doi"]

        if "ee" in dblp_data:
            entry["url"] = dblp_data["ee"]

        return self.clean_entry(entry)

    def pubmed_to_bibtex(self, pubmed_data, original_key):
        entry = {"ID": original_key}
        entry["ENTRYTYPE"] = "article"

        if pubmed_data.get("title"):
            entry["title"] = self.format_field_value(pubmed_data["title"], protect_case=True)

        if "authors" in pubmed_data:
            authors = []
            for author in pubmed_data["authors"]:
                name = author.get("name", "")
                if name:
                    authors.append(name)
            if authors:
                entry["author"] = " and ".join(authors)

        if "pubdate" in pubmed_data:
            pubdate = pubmed_data["pubdate"]
            year_match = re.search(r"\d{4}", pubdate)
            if year_match:
                entry["year"] = year_match.group(0)

        if pubmed_data.get("fulljournalname"):
            entry["journal"] = self.format_field_value(
                pubmed_data["fulljournalname"], protect_case=True
            )
        elif pubmed_data.get("source"):
            entry["journal"] = self.format_field_value(pubmed_data["source"], protect_case=True)

        if "volume" in pubmed_data:
            entry["volume"] = str(pubmed_data["volume"])

        if "issue" in pubmed_data:
            entry["number"] = str(pubmed_data["issue"])

        if "pages" in pubmed_data:
            entry["pages"] = pubmed_data["pages"].replace("-", "--")

        if "elocationid" in pubmed_data:
            doi_match = re.search(r"doi:\s*(.+)", pubmed_data["elocationid"])
            if doi_match:
                entry["doi"] = doi_match.group(1)

        if "articleids" in pubmed_data:
            for article_id in pubmed_data["articleids"]:
                if article_id.get("idtype") == "doi":
                    entry["doi"] = article_id.get("value", "")
                elif article_id.get("idtype") == "pubmed":
                    entry["pmid"] = article_id.get("value", "")

        return self.clean_entry(entry)

    def europe_pmc_to_bibtex(self, epmc_data, original_key):
        entry = {"ID": original_key}
        entry["ENTRYTYPE"] = "article"

        if epmc_data.get("title"):
            entry["title"] = self.format_field_value(epmc_data["title"], protect_case=True)

        if epmc_data.get("authorString"):
            authors = epmc_data["authorString"].split(", ")
            entry["author"] = " and ".join(authors)

        if "pubYear" in epmc_data:
            entry["year"] = str(epmc_data["pubYear"])

        if epmc_data.get("journalTitle"):
            entry["journal"] = self.format_field_value(epmc_data["journalTitle"], protect_case=True)

        if "journalVolume" in epmc_data:
            entry["volume"] = str(epmc_data["journalVolume"])

        if "issue" in epmc_data:
            entry["number"] = str(epmc_data["issue"])

        if "pageInfo" in epmc_data:
            entry["pages"] = epmc_data["pageInfo"].replace("-", "--")

        if "doi" in epmc_data:
            entry["doi"] = epmc_data["doi"]

        if "pmid" in epmc_data:
            entry["pmid"] = epmc_data["pmid"]

        return self.clean_entry(entry)

    def core_to_bibtex(self, core_data, original_key):
        entry = {"ID": original_key}
        entry["ENTRYTYPE"] = "article"

        if core_data.get("title"):
            entry["title"] = self.format_field_value(core_data["title"], protect_case=True)

        if "authors" in core_data:
            authors = [
                author.get("name", "") for author in core_data["authors"] if author.get("name")
            ]
            if authors:
                entry["author"] = " and ".join(authors)

        if "yearPublished" in core_data:
            entry["year"] = str(core_data["yearPublished"])
        elif "publishedDate" in core_data:
            year_match = re.search(r"\d{4}", core_data["publishedDate"])
            if year_match:
                entry["year"] = year_match.group(0)

        if core_data.get("journals"):
            entry["journal"] = self.format_field_value(core_data["journals"][0], protect_case=True)

        if "doi" in core_data:
            entry["doi"] = core_data["doi"]

        if "downloadUrl" in core_data:
            entry["url"] = core_data["downloadUrl"]

        return self.clean_entry(entry)

    def arxiv_to_bibtex(self, arxiv_entry, namespace, original_key):
        entry = {"ID": original_key}
        entry["ENTRYTYPE"] = "article"

        title_elem = arxiv_entry.find("atom:title", namespace)
        if title_elem is not None:
            title_text = title_elem.text.strip().replace("\n", " ")
            entry["title"] = self.format_field_value(title_text, protect_case=True)

        authors = []
        for author_elem in arxiv_entry.findall("atom:author", namespace):
            name_elem = author_elem.find("atom:name", namespace)
            if name_elem is not None:
                authors.append(name_elem.text.strip())
        if authors:
            entry["author"] = " and ".join(authors)

        published_elem = arxiv_entry.find("atom:published", namespace)
        if published_elem is not None:
            year = published_elem.text.strip()[:4]
            entry["year"] = year

        arxiv_id = None
        arxiv_id_elem = arxiv_entry.find("atom:id", namespace)
        if arxiv_id_elem is not None:
            arxiv_url = arxiv_id_elem.text.strip()
            arxiv_id = arxiv_url.split("/")[-1]
            arxiv_id_base = re.sub(r"v\d+$", "", arxiv_id)
            entry["eprint"] = arxiv_id
            entry["archiveprefix"] = "arXiv"

        primary_category = arxiv_entry.find(
            "arxiv:primary_category", {"arxiv": "http://arxiv.org/schemas/atom"}
        )
        if primary_category is not None:
            entry["primaryclass"] = primary_category.get("term", "")

        journal_elem = arxiv_entry.find(
            "arxiv:journal_ref", {"arxiv": "http://arxiv.org/schemas/atom"}
        )
        if journal_elem is not None and journal_elem.text:
            entry["journal"] = self.format_field_value(journal_elem.text.strip(), protect_case=True)
        else:
            entry["journal"] = self.format_field_value("arXiv", protect_case=True)

        doi_elem = arxiv_entry.find("arxiv:doi", {"arxiv": "http://arxiv.org/schemas/atom"})
        if doi_elem is not None and doi_elem.text:
            entry["doi"] = doi_elem.text.strip()
        elif arxiv_id:
            arxiv_id_base = re.sub(r"v\d+$", "", arxiv_id)
            entry["doi"] = f"10.48550/arxiv.{arxiv_id_base}"

        return self.clean_entry(entry)

    def openalex_to_bibtex(self, openalex_data, original_key):
        entry = {"ID": original_key}

        work_type = openalex_data.get("type", "article")
        type_mapping = {
            "journal-article": "article",
            "book-chapter": "incollection",
            "book": "book",
            "proceedings-article": "inproceedings",
            "article": "article",
        }
        entry["ENTRYTYPE"] = type_mapping.get(work_type, "article")

        if openalex_data.get("title"):
            entry["title"] = self.format_field_value(openalex_data["title"], protect_case=True)

        if openalex_data.get("authorships"):
            authors = []
            for authorship in openalex_data["authorships"]:
                if authorship.get("author"):
                    author_name = authorship["author"].get("display_name", "")
                    if author_name:
                        authors.append(author_name)
            if authors:
                entry["author"] = " and ".join(authors)

        if openalex_data.get("publication_year"):
            entry["year"] = str(openalex_data["publication_year"])

        if openalex_data.get("primary_location"):
            location = openalex_data["primary_location"]
            if location.get("source"):
                source = location["source"]
                if source.get("display_name"):
                    if entry["ENTRYTYPE"] == "article":
                        entry["journal"] = self.format_field_value(
                            source["display_name"], protect_case=True
                        )
                    elif entry["ENTRYTYPE"] == "inproceedings":
                        entry["booktitle"] = self.format_field_value(
                            source["display_name"], protect_case=True
                        )

        if openalex_data.get("biblio"):
            biblio = openalex_data["biblio"]
            if biblio.get("volume"):
                entry["volume"] = str(biblio["volume"])
            if biblio.get("issue"):
                entry["number"] = str(biblio["issue"])
            if biblio.get("first_page") and biblio.get("last_page"):
                entry["pages"] = f"{biblio['first_page']}--{biblio['last_page']}"
            elif biblio.get("first_page"):
                entry["pages"] = str(biblio["first_page"])

        if openalex_data.get("doi"):
            doi = openalex_data["doi"].replace("https://doi.org/", "")
            entry["doi"] = doi

        if "host_organization" in openalex_data and openalex_data.get("host_organization"):
            entry["publisher"] = openalex_data["host_organization"].get("display_name", "")

        return self.clean_entry(entry)

    def crossref_to_bibtex(self, crossref_data, original_key):
        entry = {"ID": original_key}

        entry_type = crossref_data.get("type", "article")
        type_mapping = {
            "journal-article": "article",
            "book-chapter": "incollection",
            "book": "book",
            "proceedings-article": "inproceedings",
            "posted-content": "unpublished",
        }
        entry["ENTRYTYPE"] = type_mapping.get(entry_type, "article")

        if crossref_data.get("title"):
            entry["title"] = self.format_field_value(crossref_data["title"][0], protect_case=True)

        if "author" in crossref_data:
            authors = []
            for author in crossref_data["author"]:
                if "family" in author:
                    if "given" in author:
                        author_name = f"{author['family']}, {author['given']}"
                    else:
                        author_name = author["family"]
                    authors.append(author_name)
            if authors:
                entry["author"] = " and ".join(authors)

        if "published" in crossref_data:
            date_parts = crossref_data["published"].get("date-parts", [[]])[0]
            if date_parts:
                entry["year"] = str(date_parts[0])
        elif "published-print" in crossref_data:
            date_parts = crossref_data["published-print"].get("date-parts", [[]])[0]
            if date_parts:
                entry["year"] = str(date_parts[0])

        if crossref_data.get("container-title"):
            container = crossref_data["container-title"][0]
            if entry["ENTRYTYPE"] == "article":
                entry["journal"] = self.format_field_value(container, protect_case=True)
            elif entry["ENTRYTYPE"] == "inproceedings":
                entry["booktitle"] = self.format_field_value(container, protect_case=False)

        if "volume" in crossref_data:
            entry["volume"] = str(crossref_data["volume"])

        if "issue" in crossref_data:
            entry["number"] = str(crossref_data["issue"])

        if "page" in crossref_data:
            entry["pages"] = crossref_data["page"].replace("-", "--")

        if "publisher" in crossref_data:
            entry["publisher"] = crossref_data["publisher"]

        if "DOI" in crossref_data:
            entry["doi"] = crossref_data["DOI"]

        return self.clean_entry(entry)

    def biorxiv_to_bibtex(self, biorxiv_data, original_key):
        entry = {"ID": original_key}
        entry["ENTRYTYPE"] = "article"

        if biorxiv_data.get("title"):
            entry["title"] = self.format_field_value(biorxiv_data["title"], protect_case=True)

        if biorxiv_data.get("authors"):
            authors = []
            for author in biorxiv_data["authors"]:
                if isinstance(author, dict):
                    name = author.get("name", "")
                else:
                    name = str(author)
                if name:
                    authors.append(name)
            if authors:
                entry["author"] = " and ".join(authors)

        if biorxiv_data.get("date"):
            date_str = biorxiv_data["date"]
            year_match = re.search(r"\d{4}", date_str)
            if year_match:
                entry["year"] = year_match.group(0)

        if biorxiv_data.get("journal"):
            entry["journal"] = self.format_field_value(biorxiv_data["journal"], protect_case=True)
        else:
            entry["journal"] = self.format_field_value("bioRxiv", protect_case=True)

        if biorxiv_data.get("doi"):
            entry["doi"] = biorxiv_data["doi"]

        if biorxiv_data.get("biorxiv_url"):
            entry["url"] = biorxiv_data["biorxiv_url"]

        if biorxiv_data.get("preprint_url"):
            entry["url"] = biorxiv_data["preprint_url"]

        if biorxiv_data.get("version"):
            entry["note"] = f"Version {biorxiv_data['version']}"

        if biorxiv_data.get("category"):
            entry["keywords"] = biorxiv_data["category"]

        return self.clean_entry(entry)

    def clean_bibtex_braces(self, bibtex_str):
        """
        Remove double curly braces {{...}} from BibTeX string.
        """
        lines = bibtex_str.split("\n")
        cleaned_lines = []
        for line in lines:
            # Match field assignment: key = {{value}} or key = {{value}},
            match = re.search(r"(\s*\w+\s*=\s*)\{\{(.*?)\}\}(,?.*)", line)
            if match:
                prefix = match.group(1)
                content = match.group(2)
                suffix = match.group(3)
                # Reconstruct with single braces
                cleaned_line = f"{prefix}{{{content}}}{suffix}"
                cleaned_lines.append(cleaned_line)
            else:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def google_scholar_to_bibtex(self, bibtex_str, original_key):
        # Clean braces first
        cleaned_bibtex_str = self.clean_bibtex_braces(bibtex_str)
        parser = BibTexParser(common_strings=True)

        try:
            db = bibtexparser.loads(cleaned_bibtex_str, parser)
        except Exception:
            try:
                db = bibtexparser.loads(bibtex_str, parser)
            except (AttributeError, KeyError, TypeError, ValueError):
                return {"ID": original_key, "ENTRYTYPE": "misc", "note": "Failed to parse"}

        if not db.entries:
            return {"ID": original_key, "ENTRYTYPE": "misc"}

        entry = db.entries[0]
        result = {"ID": original_key, "ENTRYTYPE": entry.get("ENTRYTYPE", "article")}

        for key, value in entry.items():
            if key not in ["ID", "ENTRYTYPE"]:
                result[key] = self.format_field_value(value, protect_case=True)

        return self.clean_entry(result)

    def compare_entries(self, original, updated):
        differences = {}
        all_keys = set(original.keys()) | set(updated.keys())

        for key in all_keys:
            if key in ["ID"]:
                continue

            orig_val = str(original.get(key, "") or "").strip()
            upd_val = str(updated.get(key, "") or "").strip()

            orig_val_clean = re.sub(r"\{|\}", "", orig_val).lower()
            upd_val_clean = re.sub(r"\{|\}", "", upd_val).lower()

            if orig_val_clean != upd_val_clean:
                differences[key] = {"original": orig_val, "updated": upd_val}

        return differences

    def _create_bibtex_writer(self):
        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = None
        writer.common_strings = True
        writer.COMMON_STRINGS = []
        writer.display_order = [
            "title",
            "author",
            "editor",
            "journal",
            "booktitle",
            "volume",
            "number",
            "pages",
            "year",
            "month",
            "publisher",
            "organization",
            "institution",
            "address",
            "edition",
            "chapter",
            "series",
            "note",
            "doi",
            "url",
            "eprint",
            "archiveprefix",
            "primaryclass",
            "pmid",
            "howpublished",
            "school",
        ]
        return writer

    def entry_to_bibtex(self, entry):
        db = BibDatabase()
        db.entries.append(self.clean_entry_for_writing(entry))
        content = self._create_bibtex_writer().write(db)
        return content.replace("arXiv (Cornell University)", "arXiv")

    def generate_crossref_key(self, crossref_data, doi):
        author = ""
        authors = crossref_data.get("author", [])
        if authors:
            author = authors[0].get("family", "")
        year = ""
        if "published" in crossref_data:
            date_parts = crossref_data["published"].get("date-parts", [[]])[0]
            if date_parts:
                year = str(date_parts[0])
        title_word = ""
        titles = crossref_data.get("title", [])
        if titles:
            words = re.findall(r"[A-Za-z0-9]+", titles[0])
            if words:
                title_word = words[0]

        raw_key = "".join(part for part in [author, year, title_word] if part)
        if not raw_key:
            raw_key = self.canonicalize_doi(doi).split("/")[-1]
        key = re.sub(r"[^A-Za-z0-9_:-]+", "_", raw_key).strip("_:-")
        return key or "crossref_entry"

    def bibtex_from_doi(self, doi, key=None):
        result = self.query_crossref_by_doi(doi)
        if not result:
            return None
        crossref_data = result[1]
        entry_key = key or self.generate_crossref_key(crossref_data, doi)
        entry = self.crossref_to_bibtex(crossref_data, entry_key)
        return self.entry_to_bibtex(entry)
