#!/usr/bin/env python3
"""Regression checks for the category-scout-reflection scoring script."""

from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "category-scout-reflection"
MODULE_PATH = SKILL_DIR / "scripts" / "category_scout_reflection.py"


def load_module():
    spec = importlib.util.spec_from_file_location("category_scout_reflection", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "item_id",
        "query",
        "source_type",
        "source_name",
        "url",
        "title",
        "product_or_topic",
        "evidence_text",
        "raw_user_quote",
        "user_problem",
        "problem_dimension",
        "problem_severity",
        "frequency_signal",
        "frequency_evidence",
        "requested_fix",
        "parameter_to_verify",
        "supplier_test",
        "polarity",
        "notes",
        "captured_date",
        "screenshot_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_scored(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["item_id"]: row for row in csv.DictReader(f)}


def main() -> None:
    module = load_module()
    profile = {
        "category": "portable_blender",
        "display_name": "Portable Blender",
        "target_market": "US ecommerce",
        "research_mode": "user_problem_first",
        "search_need": "Test user-problem-first scoring behavior.",
        "primary_source_types": ["ecommerce_review", "ecommerce_qa"],
        "secondary_source_types": ["expert_review", "shopping_article"],
        "source_quota": {
            "min_user_problem_rows": 1,
            "min_negative_or_question_rows": 1,
            "max_media_rows": 1,
            "min_distinct_user_sources": 1,
        },
        "must_include_keywords": ["portable blender", "personal blender"],
        "nice_to_have_keywords": ["travel", "usb"],
        "exclude_keywords": ["commercial blender", "food processor"],
        "negative_dimensions": {
            "leaking": ["leaking", "spill"],
            "power": ["weak", "struggles", "chunks"],
        },
        "improvement_rules": {
            "leaking": "Run side-position leak tests before sourcing.",
            "power": "Validate frozen-fruit performance before claims.",
        },
    }
    rows = [
        {
            "item_id": "T001",
            "query": "portable blender review",
            "source_type": "expert_review",
            "source_name": "Generic Media",
            "url": "https://example.com/media",
            "title": "Portable Blender Review",
            "product_or_topic": "Portable blender",
            "evidence_text": "This article says a portable blender is useful for travel.",
            "raw_user_quote": "",
            "user_problem": "",
            "problem_dimension": "power",
            "problem_severity": "unknown",
            "frequency_signal": "unknown",
            "frequency_evidence": "Media article only.",
            "requested_fix": "",
            "parameter_to_verify": "",
            "supplier_test": "",
            "polarity": "positive",
            "notes": "Media should not become main evidence.",
            "captured_date": "2026-06-23",
            "screenshot_path": "",
        },
        {
            "item_id": "T002",
            "query": "portable blender leaking travel",
            "source_type": "ecommerce_review",
            "source_name": "Example Review",
            "url": "https://example.com/portable-review/review-002",
            "title": "Portable Blender Customer Reviews",
            "product_or_topic": "Personal blender",
            "evidence_text": "Review text: It leaks when placed on its side. A portable blender travel cup shows leaking when placed on its side.",
            "raw_user_quote": "It leaks when placed on its side.",
            "user_problem": "Users complain the bottle leaks in a gym bag.",
            "problem_dimension": "leaking",
            "problem_severity": "high",
            "frequency_signal": "repeated",
            "frequency_evidence": "Multiple reviews and Q&A mention bag leakage.",
            "requested_fix": "Run side-position leak tests before sourcing.",
            "parameter_to_verify": "Side-position leakage after 30 minutes.",
            "supplier_test": "Fill to max line and store sideways in a bag.",
            "polarity": "negative",
            "notes": "Weakness should create a row-cited improvement direction.",
            "captured_date": "2026-06-23",
            "screenshot_path": "",
        },
    ]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        profile_path = tmp_path / "profile.json"
        observations_path = tmp_path / "observations.csv"
        out_dir = tmp_path / "out"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        write_csv(observations_path, rows)

        module.run(profile_path, observations_path, out_dir)
        scored = read_scored(out_dir / "scored_observations.csv")
        report = (out_dir / "reflection_report.md").read_text(encoding="utf-8")

    assert scored["T001"]["source_group"] == "secondary", scored["T001"]
    assert scored["T001"]["status"] in {"weak", "reject"}, scored["T001"]
    assert scored["T002"]["status"] in {"review", "strong"}, scored["T002"]
    assert int(scored["T002"]["problem_value_score"]) >= 80, scored["T002"]
    assert scored["T002"]["parameter_to_verify"] == "Side-position leakage after 30 minutes.", scored["T002"]
    assert "supported by T002" in scored["T002"]["improvement_direction"]
    assert "T002" in report and "用户真实问题" in report
    print("category-scout-reflection regression checks passed")


if __name__ == "__main__":
    main()
