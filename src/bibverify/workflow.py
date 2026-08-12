"""Verification orchestration, reporting, and atomic output handling."""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from bibtexparser.bibdatabase import BibDatabase


class WorkflowMixin:
    def check_all_entries(self):
        total = len(self.db.entries)

        for idx, entry in enumerate(self.db.entries, 1):
            entry_key = entry["ID"]
            title = entry.get("title", "")

            print(
                f"\n{self.lang.get_text('checking_entry', current=idx, total=total, key=entry_key)}"
            )
            print(f"  {self.lang.get_text('original_title', title=self.clean_title(title))}")

            query_result = self.query_multi_platform(title, entry)

            if query_result:
                platform = query_result[0]

                if platform == "crossref":
                    crossref_data = query_result[1]
                    matched_title = crossref_data.get("title", [""])[0]
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.crossref_to_bibtex(crossref_data, entry_key)
                elif platform == "arxiv":
                    arxiv_entry = query_result[1]
                    namespace = query_result[2]
                    title_elem = arxiv_entry.find("atom:title", namespace)
                    matched_title = (
                        title_elem.text.strip().replace("\n", " ") if title_elem is not None else ""
                    )
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.arxiv_to_bibtex(arxiv_entry, namespace, entry_key)
                elif platform == "openalex":
                    openalex_data = query_result[1]
                    matched_title = openalex_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.openalex_to_bibtex(openalex_data, entry_key)
                elif platform == "semantic_scholar":
                    ss_data = query_result[1]
                    matched_title = ss_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.semantic_scholar_to_bibtex(ss_data, entry_key)
                elif platform == "dblp":
                    dblp_data = query_result[1]
                    matched_title = dblp_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.dblp_to_bibtex(dblp_data, entry_key)
                elif platform == "pubmed":
                    pubmed_data = query_result[1]
                    matched_title = pubmed_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.pubmed_to_bibtex(pubmed_data, entry_key)
                elif platform == "europe_pmc":
                    epmc_data = query_result[1]
                    matched_title = epmc_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.europe_pmc_to_bibtex(epmc_data, entry_key)
                elif platform == "core":
                    core_data = query_result[1]
                    matched_title = core_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.core_to_bibtex(core_data, entry_key)
                elif platform == "biorxiv":
                    biorxiv_data = query_result[1]
                    matched_title = biorxiv_data.get("title", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                    updated_entry = self.biorxiv_to_bibtex(biorxiv_data, entry_key)
                elif platform == "google_scholar":
                    bibtex_str = query_result[1]
                    updated_entry = self.google_scholar_to_bibtex(bibtex_str, entry_key)
                    matched_title = updated_entry.get("title", "").replace("{", "").replace("}", "")
                    print(f"  {self.lang.get_text('matched_title', title=matched_title)}")
                else:
                    print(f"  {self.lang.get_text('unknown_platform', platform=platform)}")
                    self.results["errors"].append(
                        {
                            "key": entry_key,
                            "title": title,
                            "entry": entry,
                            "error": f"未知平台: {platform}",
                        }
                    )
                    continue

                differences = self.compare_entries(entry, updated_entry)

                if differences:
                    print(f"  {self.lang.get_text('need_update', count=len(differences))}")
                    self.results["updated"].append(
                        {
                            "key": entry_key,
                            "original": entry,
                            "updated": updated_entry,
                            "differences": differences,
                            "platform": platform,
                        }
                    )
                else:
                    print(f"  {self.lang.get_text('verified_no_update')}")
                    self.results["verified"].append(
                        {"key": entry_key, "entry": entry, "platform": platform}
                    )
            else:
                print(f"  {self.lang.get_text('all_platforms_no_match')}")
                self.results["not_found"].append({"key": entry_key, "title": title, "entry": entry})

    def generate_report(self):
        output_settings = self.config.get("output_settings", {})
        if not output_settings.get("generate_report", True):
            self.last_output_files["report"] = None
            return None

        timestamp = self._timestamp()
        report_file = self.output_dir / f"bib_check_report_{timestamp}.txt"
        is_english = self.config.get("language") == "EN"
        labels = {
            "title": "BibTeX verification report" if is_english else "BibTeX 文献验证报告",
            "generated": "Generated" if is_english else "生成时间",
            "providers": "Enabled providers" if is_english else "启用平台",
            "total": "Total" if is_english else "总计检查",
            "verified": "Verified" if is_english else "验证通过",
            "updated": "Updates proposed" if is_english else "建议更新",
            "not_found": "Not found" if is_english else "未找到",
            "errors": "Errors" if is_english else "错误",
            "updates": "Proposed updates" if is_english else "建议更新的文献",
            "missing": "References requiring manual review" if is_english else "需要手动检查的文献",
            "failures": "Processing errors" if is_english else "处理错误",
            "key": "Citation key" if is_english else "文献键值",
            "source": "Source" if is_english else "数据来源",
            "field_diff": "Field differences" if is_english else "字段差异",
            "old": "Old" if is_english else "原值",
            "new": "New" if is_english else "新值",
            "entry_type": "Entry type" if is_english else "类型",
            "error": "Error" if is_english else "错误信息",
            "title_field": "Title" if is_english else "标题",
        }
        lines = [
            "=" * 80,
            labels["title"],
            f"{labels['generated']}: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            f"{labels['providers']}: {', '.join(p.upper() for p in self.enabled_platforms)}",
            "=" * 80,
            "",
            f"{labels['total']}: {len(self.db.entries)}",
            f"{labels['verified']}: {len(self.results['verified'])}",
            f"{labels['updated']}: {len(self.results['updated'])}",
            f"{labels['not_found']}: {len(self.results['not_found'])}",
            f"{labels['errors']}: {len(self.results['errors'])}",
            "",
        ]

        if self.results["updated"]:
            lines.extend(["=" * 80, labels["updates"], "=" * 80, ""])
            for item in self.results["updated"]:
                lines.extend(
                    [
                        f"{labels['key']}: {item['key']}",
                        f"{labels['title_field']}: {self.clean_title(item['original'].get('title', ''))}",
                        f"{labels['source']}: {item.get('platform', 'unknown').upper()}",
                        labels["field_diff"] + ":",
                    ]
                )
                for field, diff in item["differences"].items():
                    lines.extend(
                        [
                            f"  {field}:",
                            f"    {labels['old']}: {diff['original']}",
                            f"    {labels['new']}: {diff['updated']}",
                        ]
                    )
                lines.extend(["-" * 80, ""])

        if self.results["not_found"]:
            lines.extend(["=" * 80, labels["missing"], "=" * 80, ""])
            for item in self.results["not_found"]:
                lines.extend(
                    [
                        f"{labels['key']}: {item['key']}",
                        f"{labels['title_field']}: {self.clean_title(item['title'])}",
                        f"{labels['entry_type']}: {item['entry'].get('ENTRYTYPE', 'unknown')}",
                        "-" * 80,
                        "",
                    ]
                )

        if self.results["errors"]:
            lines.extend(["=" * 80, labels["failures"], "=" * 80, ""])
            for item in self.results["errors"]:
                lines.extend(
                    [
                        f"{labels['key']}: {item['key']}",
                        f"{labels['title_field']}: {self.clean_title(item.get('title', ''))}",
                        f"{labels['error']}: {item.get('error', 'unknown error')}",
                        "-" * 80,
                        "",
                    ]
                )

        self._atomic_write_text(report_file, "\n".join(lines) + "\n")
        report_path = str(report_file.resolve())
        print(f"\n{self.lang.get_text('report_generated', file=report_path)}")
        self.last_output_files["report"] = report_path
        return report_path

    def _output_prefix(self):
        stem = Path(self.bib_file).stem
        prefix = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", stem)
        prefix = re.sub(r"\s+", "_", prefix).strip(" ._-")[:100]
        if prefix.upper() in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }:
            prefix = f"_{prefix}"
        return prefix or "bibverify"

    def _timestamp(self):
        timestamp_format = self.config.get("output_settings", {}).get(
            "timestamp_format", "%Y%m%d_%H%M%S"
        )
        return datetime.now().strftime(timestamp_format)

    def _atomic_write_text(self, path, content, *, newline=None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        newline = self.output_newline if newline is None else newline
        normalized = content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                stream.write(normalized)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def _atomic_write_bytes(self, path, content):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def generate_updated_bib(self):
        output_settings = self.config.get("output_settings", {})
        timestamp = self._timestamp()
        output_prefix = self._output_prefix()
        backup_file = self.output_dir / f"{output_prefix}_backup_{timestamp}.bib"
        updated_file = self.output_dir / f"{output_prefix}_updated_{timestamp}.bib"
        wrong_file = self.output_dir / f"{output_prefix}_wrong_{timestamp}.bib"

        if output_settings.get("generate_backup", True):
            self._atomic_write_bytes(backup_file, Path(self.bib_file).read_bytes())
            backup_path = str(backup_file.resolve())
            print(f"\n{self.lang.get_text('backup_generated', file=backup_path)}")
            self.last_output_files["backup"] = backup_path
        else:
            self.last_output_files["backup"] = None

        updated_db = BibDatabase()
        wrong_db = BibDatabase()

        # The updated file is a complete, ready-to-use bibliography. Replace
        # accepted entries in their original order and preserve every other
        # source entry unchanged.
        replacements = {item["key"]: item["updated"] for item in self.results["updated"]}
        if self.db is not None:
            for original in self.db.entries:
                selected = replacements.get(original.get("ID"), original)
                updated_db.entries.append(self.clean_entry_for_writing(selected))
        else:
            for item in self.results["updated"]:
                updated_db.entries.append(self.clean_entry_for_writing(item["updated"]))

        # 清理未找到条目中的 None 值
        for item in self.results["not_found"]:
            cleaned_entry = self.clean_entry_for_writing(item["entry"])
            wrong_db.entries.append(cleaned_entry)

        # 清理错误条目中的 None 值
        for item in self.results["errors"]:
            cleaned_entry = self.clean_entry_for_writing(item["entry"])
            wrong_db.entries.append(cleaned_entry)

        writer = self._create_bibtex_writer()

        if self.results["updated"] and output_settings.get("generate_updated_bib", True):
            content = writer.write(updated_db).replace("arXiv (Cornell University)", "arXiv")
            self._atomic_write_text(updated_file, content)
            updated_path = str(updated_file.resolve())
            print(f"{self.lang.get_text('updated_generated', file=updated_path)}")
            print(
                f"      {self.lang.get_text('updated_count', count=len(self.results['updated']))}"
            )
            self.last_output_files["updated"] = updated_path
        else:
            print(self.lang.get_text("no_update_skip"))
            self.last_output_files["updated"] = None

        has_wrong = bool(self.results["not_found"] or self.results["errors"])
        if has_wrong and output_settings.get("generate_wrong_bib", True):
            content = writer.write(wrong_db).replace("arXiv (Cornell University)", "arXiv")
            self._atomic_write_text(wrong_file, content)
            wrong_path = str(wrong_file.resolve())
            print(f"{self.lang.get_text('wrong_generated', file=wrong_path)}")
            print(
                f"      {self.lang.get_text('wrong_count', not_found=len(self.results['not_found']), errors=len(self.results['errors']))}"
            )
            self.last_output_files["wrong"] = wrong_path
        else:
            print(self.lang.get_text("no_wrong_skip"))
            self.last_output_files["wrong"] = None

        return self.last_output_files["updated"], self.last_output_files["wrong"]

    def get_run_summary(self):
        return {
            "bib_file": self.bib_file,
            "config_file": str(self.config_file),
            "output_dir": str(self.output_dir.resolve()),
            "encoding": self.file_encoding,
            "counts": {
                "total": len(self.db.entries) if self.db else 0,
                "verified": len(self.results["verified"]),
                "updated": len(self.results["updated"]),
                "not_found": len(self.results["not_found"]),
                "errors": len(self.results["errors"]),
            },
            "files": dict(self.last_output_files),
        }

    def run(self):
        print("=" * 80)
        print(self.lang.get_text("tool_title"))
        print(
            self.lang.get_text(
                "enabled_platforms",
                count=len(self.enabled_platforms),
                platforms=", ".join([p.upper() for p in self.enabled_platforms]),
            )
        )
        print("=" * 80)

        self.load_bib_file()

        print(f"\n{self.lang.get_text('start_verification')}")
        self.check_all_entries()

        print("\n" + "=" * 80)
        print(self.lang.get_text("verification_complete"))
        print("=" * 80)
        print(f"\n{self.lang.get_text('total_checked', count=len(self.db.entries))}")
        print(f"{self.lang.get_text('verified_passed', count=len(self.results['verified']))}")
        print(f"{self.lang.get_text('need_update_count', count=len(self.results['updated']))}")
        print(f"{self.lang.get_text('not_found_count', count=len(self.results['not_found']))}")
        if self.results["errors"]:
            print(f"{self.lang.get_text('errors_count', count=len(self.results['errors']))}")

        if self.results["verified"]:
            platforms = {}
            for item in self.results["verified"]:
                platform = item.get("platform", "unknown")
                platforms[platform] = platforms.get(platform, 0) + 1
            print(f"\n{self.lang.get_text('verified_sources')}")
            for platform, count in platforms.items():
                print(f"  {platform.upper()}: {count} 条")

        if self.results["updated"]:
            platforms = {}
            for item in self.results["updated"]:
                platform = item.get("platform", "unknown")
                platforms[platform] = platforms.get(platform, 0) + 1
            print(f"\n{self.lang.get_text('update_sources')}")
            for platform, count in platforms.items():
                print(f"  {platform.upper()}: {count} 条")

        print("\n" + "=" * 80)
        print(self.lang.get_text("generating_files"))
        print("=" * 80)

        self.generate_report()
        self.generate_updated_bib()
        return self.get_run_summary()
