#!/usr/bin/env python3
"""Minimal regression tests for category_scout_reflection.py."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local-skills/category-scout-reflection/scripts/category_scout_reflection.py"
PROFILE = ROOT / "tests/category_scout_reflection/edge_profile.json"
OBSERVATIONS = ROOT / "tests/category_scout_reflection/edge_observations.csv"
OUT = ROOT / "category-scout-output/tests"
BLENDER_PROFILE = ROOT / "examples/portable_blender/profile.json"
BLENDER_OBSERVATIONS = ROOT / "examples/portable_blender/observations_2026-06-22.csv"
BLENDER_OUT = ROOT / "category-scout-output/tests_blender_fixture"
ICE_PROFILE = ROOT / "examples/portable_ice_maker/profile.json"
ICE_OBSERVATIONS = ROOT / "examples/portable_ice_maker/observations_2026-06-23.csv"
ICE_OUT = ROOT / "category-scout-output/tests_ice_fixture"
MEDIA_ONLY_PROFILE = ROOT / "examples/media_only_negative/profile.json"
MEDIA_ONLY_OBSERVATIONS = ROOT / "examples/media_only_negative/observations.csv"
MEDIA_ONLY_OUT = ROOT / "category-scout-output/tests_media_only_negative"


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(PROFILE),
            "--observations",
            str(OBSERVATIONS),
            "--out",
            str(OUT),
        ],
        check=True,
    )

    with (OUT / "scored_observations.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = {row["item_id"]: row for row in csv.DictReader(f)}
    dashboard = (OUT / "dashboard.html").read_text(encoding="utf-8")

    assert rows["E001"]["status"] in {"review", "strong"}, rows["E001"]
    assert rows["E001"]["source_group"] == "primary", rows["E001"]
    assert int(rows["E001"]["source_score"]) == 20, rows["E001"]
    assert int(rows["E001"]["problem_value_score"]) >= 80, rows["E001"]
    assert rows["E001"]["parameter_to_verify"] == "Frozen fruit chunk size after 3 cycles.", rows["E001"]

    assert rows["E002"]["status"] in {"weak", "reject"}, rows["E002"]
    assert rows["E002"]["source_group"] == "secondary", rows["E002"]
    assert "Secondary/background source" in rows["E002"]["reflection_note"], rows["E002"]

    assert rows["E003"]["status"] == "reject", rows["E003"]
    assert "Generic praise only" in rows["E003"]["reflection_note"], rows["E003"]

    assert rows["E004"]["status"] == "reject", rows["E004"]
    assert "Missing user_problem field" in rows["E004"]["reflection_note"], rows["E004"]

    assert rows["E005"]["status"] == "reject", rows["E005"]
    assert "Exclude keyword hit" in rows["E005"]["reflection_note"], rows["E005"]

    assert rows["E006"]["status"] in {"review", "strong"}, rows["E006"]
    assert rows["E006"]["reported_frequency_signal"] == "many", rows["E006"]
    assert rows["E006"]["frequency_signal"] == "single", rows["E006"]
    assert "overridden by count rules" in rows["E006"]["reflection_note"], rows["E006"]
    assert rows["E006"]["supplier_test"] == "Fill to max line and shake inside a bag.", rows["E006"]
    assert "supported by E006" in rows["E006"]["improvement_direction"], rows["E006"]
    assert rows["E007"]["requested_fix"].startswith("'="), rows["E007"]
    assert 'href="javascript:alert(1)"' not in dashboard, dashboard
    assert '<a href="#">javascript:alert(1)</a>' in dashboard, dashboard
    assert rows["E008"]["status"] != "strong", rows["E008"]
    assert "Missing raw_user_quote field" in rows["E008"]["reflection_note"], rows["E008"]

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(BLENDER_PROFILE),
            "--observations",
            str(BLENDER_OBSERVATIONS),
            "--out",
            str(BLENDER_OUT),
        ],
        check=True,
    )
    blender_report = (BLENDER_OUT / "reflection_report.md").read_text(encoding="utf-8")
    assert "# 便携榨汁杯 用户问题驱动选品审查报告" in blender_report, blender_report
    assert "搅拌动力" in blender_report, blender_report
    assert "台式制冰机" not in blender_report, blender_report
    assert "portable_ice_maker" not in blender_report, blender_report

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(ICE_PROFILE),
            "--observations",
            str(ICE_OBSERVATIONS),
            "--out",
            str(ICE_OUT),
        ],
        check=True,
    )
    ice_report = (ICE_OUT / "reflection_report.md").read_text(encoding="utf-8")
    assert "# 台式制冰机 用户问题驱动选品审查报告" in ice_report, ice_report
    assert "清洗/除垢" in ice_report, ice_report
    assert "便携榨汁杯" not in ice_report, ice_report
    assert "portable_blender" not in ice_report, ice_report

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--profile",
            str(MEDIA_ONLY_PROFILE),
            "--observations",
            str(MEDIA_ONLY_OBSERVATIONS),
            "--out",
            str(MEDIA_ONLY_OUT),
        ],
        check=True,
    )
    media_report = (MEDIA_ONLY_OUT / "reflection_report.md").read_text(encoding="utf-8")
    with (MEDIA_ONLY_OUT / "scored_observations.csv").open(encoding="utf-8-sig", newline="") as f:
        media_rows = list(csv.DictReader(f))
    assert "审查结论：不通过，需要补采真实用户问题证据" in media_report, media_report
    assert "通过用户问题初筛" not in media_report, media_report
    assert all(row["source_group"] == "secondary" for row in media_rows), media_rows
    assert all(row["status"] in {"weak", "reject"} for row in media_rows), media_rows
    assert "真实用户问题行 | 0" in media_report, media_report

    print("category_scout_reflection tests passed")


if __name__ == "__main__":
    main()
