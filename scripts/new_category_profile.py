#!/usr/bin/env python3
"""Create a lightweight category profile and observations template."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PROFILE = ROOT / "local-skills/category-scout-reflection/assets/category_profile_template.json"
OBSERVATION_FIELDS = [
    "item_id",
    "source_type",
    "source_name",
    "url",
    "screenshot_path",
    "title",
    "product_or_topic",
    "evidence_text",
    "raw_user_quote",
    "user_problem",
    "problem_dimension",
    "polarity",
    "captured_date",
]


def slug_words(value: str) -> list[str]:
    return [part for part in value.replace("_", " ").replace("-", " ").lower().split() if part]


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new category profile and observations CSV.")
    parser.add_argument("--category", required=True, help="Category id, e.g. electric_lunch_box")
    parser.add_argument("--display-name", required=True, help='English display name, e.g. "Electric Lunch Box"')
    parser.add_argument("--display-name-zh", required=True, help='Chinese display name, e.g. "电热饭盒"')
    parser.add_argument("--out", required=True, type=Path, help="Output directory, e.g. examples/electric_lunch_box")
    args = parser.parse_args()

    with TEMPLATE_PROFILE.open(encoding="utf-8") as f:
        profile = json.load(f)

    words = slug_words(args.category)
    profile.update(
        {
            "category": args.category,
            "display_name": args.display_name,
            "display_name_zh": args.display_name_zh,
            "search_need": f"Find real user problems that can guide product selection for {args.display_name}.",
            "search_need_zh": f"优先采集{args.display_name_zh}真实用户评论、问答和社媒讨论，提取可聚类的用户问题。",
            "must_include_keywords": [args.display_name.lower(), args.category.replace("_", " "), *words],
            "nice_to_have_keywords": ["cleaning", "noise", "reliability", "size", "safety"],
            "exclude_keywords": ["accessory", "replacement part", "manual"],
        }
    )

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with (args.out / "observations.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OBSERVATION_FIELDS)
        writer.writeheader()
        writer.writerow(
            {
                "item_id": "TODO001",
                "source_type": "ecommerce_review",
                "source_name": "TODO platform",
                "url": "https://example.com/concrete-review-or-thread",
                "screenshot_path": "",
                "title": "TODO concrete review, Q&A, thread, or video title",
                "product_or_topic": args.display_name,
                "evidence_text": "TODO copied evidence text that includes the raw user quote.",
                "raw_user_quote": "TODO exact short user quote.",
                "user_problem": "TODO concise user problem extracted from the quote.",
                "problem_dimension": "TODO_dimension",
                "polarity": "negative",
                "captured_date": "YYYY-MM-DD",
            }
        )

    print(f"Wrote {args.out / 'profile.json'}")
    print(f"Wrote {args.out / 'observations.csv'}")


if __name__ == "__main__":
    main()
