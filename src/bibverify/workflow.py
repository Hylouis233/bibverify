"""Verification orchestration, reporting, and atomic output handling."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from bibtexparser.bibdatabase import BibDatabase

from bibverify.merge import merge_entries
from bibverify.models import EntryStatus

RESULT_BUCKETS = (
    "verified",
    "updated",
    "ambiguous",
    "not_found",
    "source_unavailable",
    "identifier_conflict",
    "invalid_input",
    "errors",
)
REVIEW_BUCKETS = RESULT_BUCKETS[2:]


class WorkflowMixin:
    def check_all_entries(self) -> None:
        """Verify entries while keeping every non-equivalent outcome distinct."""
        entries = self.db.entries if self.db else []
        duplicate_keys = {
            key
            for key, count in Counter(entry.get("ID") for entry in entries).items()
            if key and count > 1
        }
        for idx, entry in enumerate(entries, 1):
            entry_key = str(entry.get("ID") or f"__missing_key_{idx}")
            title = str(entry.get("title", ""))
            print(
                f"\n{self.lang.get_text('checking_entry', current=idx, total=len(entries), key=entry_key)}"
            )
            print(f"  {self.lang.get_text('original_title', title=self.clean_title(title))}")

            if not entry.get("ID") or entry_key in duplicate_keys:
                reason = (
                    "Missing citation key." if not entry.get("ID") else "Duplicate citation key."
                )
                self.results["invalid_input"].append(
                    self._entry_result(entry_key, title, entry, reason=reason, complete=False)
                )
                continue

            outcome = self.query_multi_platform_result(title, entry)
            common = self._entry_result(
                entry_key,
                title,
                entry,
                reason=outcome.reason,
                complete=outcome.complete,
                confidence=(outcome.best_candidate.confidence if outcome.best_candidate else None),
                provider_status=[result.to_dict() for result in outcome.provider_results],
                candidates=([outcome.best_candidate.to_dict()] if outcome.best_candidate else []),
            )

            bucket = {
                EntryStatus.AMBIGUOUS: "ambiguous",
                EntryStatus.NOT_FOUND: "not_found",
                EntryStatus.SOURCE_UNAVAILABLE: "source_unavailable",
                EntryStatus.IDENTIFIER_CONFLICT: "identifier_conflict",
                EntryStatus.INVALID_INPUT: "invalid_input",
            }.get(outcome.status)
            if bucket:
                common["status"] = outcome.status.value
                self.results[bucket].append(common)
                continue

            candidate = outcome.best_candidate
            if candidate is None:
                common.update(status=EntryStatus.SOURCE_UNAVAILABLE.value)
                self.results["source_unavailable"].append(common)
                continue

            threshold = float(
                self.config.get("query_settings", {}).get("auto_update_threshold", 0.92)
            )
            merged = merge_entries(
                entry,
                candidate.entry,
                source=candidate.provider,
                confidence=candidate.confidence,
                auto_update_threshold=threshold,
            )
            decisions = [decision.to_dict() for decision in merged.decisions]
            meaningful = [
                decision
                for decision in decisions
                if not decision["normalized_equal"] and decision["action"] != "keep_original"
            ]
            if meaningful:
                common.update(
                    status=EntryStatus.METADATA_MISMATCH.value,
                    platform=candidate.provider,
                    updated=merged.entry,
                    differences=merged.differences,
                    field_diffs=decisions,
                )
                self.results["updated"].append(common)
                print(f"  {self.lang.get_text('need_update', count=len(meaningful))}")
            else:
                common.update(
                    status=EntryStatus.VERIFIED.value,
                    platform=candidate.provider,
                    field_diffs=decisions,
                )
                self.results["verified"].append(common)
                print(f"  {self.lang.get_text('verified_no_update')}")

    @staticmethod
    def _entry_result(
        key: str,
        title: str,
        entry: dict[str, Any],
        *,
        reason: str,
        complete: bool,
        confidence: float | None = None,
        provider_status: list[dict[str, Any]] | None = None,
        candidates: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "title": title,
            "entry": entry,
            "complete": complete,
            "confidence": round(confidence, 4) if confidence is not None else None,
            "reason": reason,
            "candidates": candidates or [],
            "provider_status": provider_status or [],
        }

    def _all_result_entries(self) -> list[dict[str, Any]]:
        return [item for bucket in RESULT_BUCKETS for item in self.results.get(bucket, [])]

    def _report_payload(self) -> dict[str, Any]:
        counts = self._counts()
        result_entries = self._all_result_entries()
        complete = (
            len(result_entries) == counts["total"]
            and all(item.get("complete", False) for item in result_entries)
            and not (counts["errors"] or counts["invalid_input"])
        )
        entries = []
        for item in result_entries:
            serialized = {
                key: value
                for key, value in item.items()
                if key not in {"entry", "original", "updated"}
            }
            entries.append(serialized)
        return {
            "schema_version": "1.0",
            "input": str(Path(self.bib_file).resolve()),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "complete": complete,
            "counts": counts,
            "entries": entries,
        }

    def generate_report(self) -> str | None:
        settings = self.config.get("output_settings", {})
        if not settings.get("generate_report", True) or self.dry_run:
            self.last_output_files["report"] = None
            return None
        report_format = str(settings.get("report_format", "txt")).lower()
        report_file = self.output_dir / f"bibverify_report_{self._timestamp()}.{report_format}"
        payload = self._report_payload()
        if report_format == "json":
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        elif report_format == "jsonl":
            header = {key: value for key, value in payload.items() if key != "entries"}
            rows = [{"type": "summary", **header}]
            rows.extend({"type": "entry", **entry} for entry in payload["entries"])
            content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
        elif report_format == "csv":
            stream = io.StringIO(newline="")
            fieldnames = ["key", "status", "complete", "confidence", "reason", "platform"]
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(payload["entries"])
            content = stream.getvalue()
        else:
            content = self._text_report(payload)
        self._atomic_write_text(report_file, content)
        path = str(report_file.resolve())
        self.last_output_files["report"] = path
        print(f"\n{self.lang.get_text('report_generated', file=path)}")
        return path

    def _text_report(self, payload: dict[str, Any]) -> str:
        english = self.config.get("language") == "EN"
        labels = {
            "title": "BibTeX verification report" if english else "BibTeX 书目元数据核验报告",
            "complete": "Verification complete" if english else "核验是否完整",
            "yes": "yes" if english else "是",
            "no": "no" if english else "否",
            "counts": "Counts" if english else "统计",
            "entries": "Entries requiring attention" if english else "需要人工关注的条目",
        }
        lines = [
            "=" * 80,
            labels["title"],
            f"{labels['complete']}: {labels['yes'] if payload['complete'] else labels['no']}",
            "=" * 80,
            labels["counts"] + ":",
        ]
        lines.extend(f"  {key}: {value}" for key, value in payload["counts"].items())
        lines.extend(["", labels["entries"] + ":"])
        for entry in payload["entries"]:
            if entry.get("status") == EntryStatus.VERIFIED.value:
                continue
            lines.extend(
                [
                    f"- {entry.get('key')}: {entry.get('status', 'unknown')}",
                    f"  confidence: {entry.get('confidence')}",
                    f"  reason: {entry.get('reason', '')}",
                ]
            )
            for diff in entry.get("field_diffs", []):
                if diff.get("action") != "keep_original":
                    lines.append(
                        f"  {diff['field']}: {diff['action']} ({diff['source']}, {diff['confidence']})"
                    )
        return "\n".join(lines) + "\n"

    def _output_prefix(self) -> str:
        prefix = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", Path(self.bib_file).stem)
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

    def _timestamp(self) -> str:
        return datetime.now().strftime(
            self.config.get("output_settings", {}).get("timestamp_format", "%Y%m%d_%H%M%S")
        )

    def _atomic_write_text(
        self, path: str | Path, content: str, *, newline: str | None = None, encoding: str = "utf-8"
    ) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        newline = self.output_newline if newline is None else newline
        normalized = content.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding=encoding, newline="") as stream:
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

    def _atomic_write_bytes(self, path: str | Path, content: bytes) -> None:
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

    def _merged_database(self) -> BibDatabase:
        database = BibDatabase()
        replacements = {
            item["key"]: item["updated"]
            for item in self.results["updated"]
            if item.get("differences")
        }
        for original in self.db.entries if self.db else []:
            database.entries.append(
                self.clean_entry_for_writing(replacements.get(original.get("ID"), original))
            )
        return database

    def generate_updated_bib(self) -> tuple[str | None, str | None]:
        settings = self.config.get("output_settings", {})
        self.last_output_files.setdefault("backup", None)
        self.last_output_files.setdefault("updated", None)
        self.last_output_files.setdefault("review", None)
        self.last_output_files.setdefault("applied", None)
        if self.dry_run:
            return None, None

        timestamp = self._timestamp()
        prefix = self._output_prefix()
        backup_file = self.output_dir / f"{prefix}_backup_{timestamp}.bib"
        updated_file = self.output_dir / f"{prefix}_updated_{timestamp}.bib"
        review_file = self.output_dir / f"{prefix}_review_{timestamp}.bib"
        source_bytes = Path(self.bib_file).read_bytes()

        needs_backup = bool(settings.get("generate_backup", True) or self.apply_changes)
        if needs_backup:
            self._atomic_write_bytes(backup_file, source_bytes)
            self.last_output_files["backup"] = str(backup_file.resolve())

        writer = self._create_bibtex_writer()
        merged_content = writer.write(self._merged_database()).replace(
            "arXiv (Cornell University)", "arXiv"
        )
        has_applied_updates = any(item.get("differences") for item in self.results["updated"])
        if has_applied_updates and settings.get("generate_updated_bib", True):
            self._atomic_write_text(updated_file, merged_content)
            self.last_output_files["updated"] = str(updated_file.resolve())
        if self.apply_changes and has_applied_updates:
            self._atomic_write_text(
                self.bib_file,
                merged_content,
                encoding=self.file_encoding,
            )
            self.last_output_files["applied"] = str(Path(self.bib_file).resolve())

        review_db = BibDatabase()
        for bucket in REVIEW_BUCKETS:
            for item in self.results.get(bucket, []):
                if item.get("entry"):
                    review_db.entries.append(self.clean_entry_for_writing(item["entry"]))
        if review_db.entries and settings.get(
            "generate_review_bib", settings.get("generate_wrong_bib", True)
        ):
            review_content = writer.write(review_db).replace("arXiv (Cornell University)", "arXiv")
            self._atomic_write_text(review_file, review_content)
            self.last_output_files["review"] = str(review_file.resolve())
        # v0.3 compatibility key; the new name avoids calling an unverified entry "wrong".
        self.last_output_files["wrong"] = self.last_output_files["review"]
        return self.last_output_files["updated"], self.last_output_files["review"]

    def _counts(self) -> dict[str, int]:
        counts = {bucket: len(self.results.get(bucket, [])) for bucket in RESULT_BUCKETS}
        counts["total"] = len(self.db.entries) if self.db else 0
        return {"total": counts.pop("total"), **counts}

    def get_run_summary(self) -> dict[str, Any]:
        payload = self._report_payload()
        return {
            "schema_version": payload["schema_version"],
            "bib_file": str(Path(self.bib_file).resolve()),
            "config_file": str(self.config_file),
            "output_dir": str(self.output_dir.resolve()),
            "encoding": self.file_encoding,
            "complete": payload["complete"],
            "dry_run": self.dry_run,
            "applied": bool(self.last_output_files.get("applied")),
            "counts": payload["counts"],
            "entries": payload["entries"],
            "files": dict(self.last_output_files),
        }

    def run(self) -> dict[str, Any]:
        print("=" * 80)
        print(self.lang.get_text("tool_title"))
        print(
            self.lang.get_text(
                "enabled_platforms",
                count=len(self.enabled_platforms),
                platforms=", ".join(platform.upper() for platform in self.enabled_platforms),
            )
        )
        print("=" * 80)
        self.load_bib_file()
        self.check_all_entries()
        print("\n" + "=" * 80)
        print(self.lang.get_text("verification_complete"))
        for status, count in self._counts().items():
            print(f"  {status}: {count}")
        self.generate_report()
        self.generate_updated_bib()
        return self.get_run_summary()
