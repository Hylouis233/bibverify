"""Offline reliability benchmark for matching-policy regression testing."""

from __future__ import annotations

import json
from collections import Counter
from importlib.resources import files
from pathlib import Path
from typing import Any

from bibverify.matching import assess_match


def default_dataset() -> Path:
    """Return the benchmark dataset shipped inside the installed package."""
    return Path(str(files("bibverify.data").joinpath("benchmark_cases.json")))


def run_benchmark(path: str | Path | None = None) -> dict[str, Any]:
    path = default_dataset() if path is None else Path(path)
    cases = json.loads(path.read_text(encoding="utf-8"))
    confusion: Counter[tuple[str, str]] = Counter()
    rows = []
    for case in cases:
        result = assess_match(case["original"], case["candidate"])
        expected = case["expected"]
        predicted = result.status.value
        confusion[(expected, predicted)] += 1
        rows.append(
            {
                "id": case["id"],
                "expected": expected,
                "predicted": predicted,
                "correct": expected == predicted,
                "score": round(result.score, 4),
            }
        )

    positive = {"matched"}
    true_positive = sum(
        count
        for (expected, predicted), count in confusion.items()
        if expected in positive and predicted in positive
    )
    false_positive = sum(
        count
        for (expected, predicted), count in confusion.items()
        if expected not in positive and predicted in positive
    )
    false_negative = sum(
        count
        for (expected, predicted), count in confusion.items()
        if expected in positive and predicted not in positive
    )
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    )
    correct = sum(row["correct"] for row in rows)
    return {
        "schema_version": "1.0",
        "cases": len(rows),
        "accuracy": round(correct / len(rows), 4) if rows else 0.0,
        "match_precision": round(precision, 4),
        "match_recall": round(recall, 4),
        "wrong_auto_match_rate": round(false_positive / len(rows), 4) if rows else 0.0,
        "results": rows,
    }
