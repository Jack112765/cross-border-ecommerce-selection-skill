#!/usr/bin/env python3
"""Score category evidence with a user-problem-first reflection model."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_PRIMARY_SOURCE_TYPES = [
    "ecommerce_review",
    "ecommerce_qa",
    "reddit_thread",
    "youtube_comment",
    "tiktok_comment",
    "support_forum",
]
DEFAULT_SECONDARY_SOURCE_TYPES = [
    "expert_review",
    "shopping_article",
    "trend_article",
    "news_recall",
]
SUPPORTED_SOURCE_TYPES = set(DEFAULT_PRIMARY_SOURCE_TYPES + DEFAULT_SECONDARY_SOURCE_TYPES)
VALID_POLARITIES = {"positive", "negative", "mixed", "risk", "question", "unknown"}
VALID_SEVERITIES = {"low", "medium", "high", "unknown"}
VALID_FREQUENCY = {"single", "repeated", "many", "unknown"}

STATUS_LABELS_ZH = {
    "strong": "强用户问题证据",
    "review": "待人工复核",
    "weak": "弱匹配/背景",
    "reject": "剔除/跑题",
}
SOURCE_TYPE_LABELS_ZH = {
    "ecommerce_review": "电商用户评论",
    "ecommerce_qa": "电商问答",
    "reddit_thread": "Reddit 讨论",
    "youtube_comment": "YouTube 评论",
    "tiktok_comment": "TikTok 评论",
    "support_forum": "支持论坛",
    "expert_review": "专业评测",
    "shopping_article": "购物推荐文章",
    "trend_article": "趋势文章",
    "news_recall": "新闻/召回",
}
SEVERITY_LABELS_ZH = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "unknown": "未知",
}
FREQUENCY_LABELS_ZH = {
    "single": "单条",
    "repeated": "重复出现",
    "many": "多人集中出现",
    "unknown": "未知",
}
DIMENSION_LABELS_ZH = {
    "portability": "便携性",
    "convenience": "使用便利性",
    "power": "搅拌动力",
    "quiet": "低噪音",
    "insulation": "保冷/保温",
    "leak_resistance": "防漏能力",
    "battery": "续航/充电",
    "cleaning": "清洁便利性",
    "leaking": "漏液风险",
    "safety": "安全风险",
    "noise": "噪音风险",
    "usage_sensitivity": "使用门槛",
    "reliability": "可靠性",
    "size": "尺寸/重量",
    "melting": "融化/保温问题",
    "drainage": "排水问题",
    "scale": "水垢/硬水",
}
GENERIC_TERMS = {"best", "cheap", "popular", "top", "great", "good", "viral", "trending"}
STOPWORDS = {
    "about",
    "after",
    "and",
    "best",
    "cheap",
    "from",
    "good",
    "great",
    "into",
    "popular",
    "review",
    "that",
    "the",
    "this",
    "with",
}

REQUIRED_COLUMNS = [
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
BACKFILLABLE_COLUMNS = {
    "query",
    "platform",
    "brand",
    "product_model",
    "review_rating",
    "review_date",
    "review_count_signal",
    "source_locator",
    "problem_severity",
    "frequency_signal",
    "evidence_count",
    "frequency_count",
    "product_count",
    "platform_count",
    "frequency_evidence",
    "requested_fix",
    "parameter_to_verify",
    "supplier_test",
    "listing_guardrail",
    "notes",
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def display_name(profile: dict) -> str:
    return profile.get("display_name_zh") or profile.get("display_name") or profile["category"]


def search_need(profile: dict) -> str:
    return profile.get("search_need_zh") or profile.get("search_need", "")


def primary_source_types(profile: dict) -> list[str]:
    return profile.get("primary_source_types") or profile.get("research_config", {}).get(
        "primary_source_types", DEFAULT_PRIMARY_SOURCE_TYPES
    )


def secondary_source_types(profile: dict) -> list[str]:
    return profile.get("secondary_source_types") or profile.get("research_config", {}).get(
        "secondary_source_types", DEFAULT_SECONDARY_SOURCE_TYPES
    )


def source_quota(profile: dict) -> dict:
    return {
        "min_user_problem_rows": 10,
        "min_negative_or_question_rows": 7,
        "max_media_rows": 3,
        "max_media_ratio": 0.2,
        "min_distinct_user_sources": 3,
        "min_distinct_platforms": 1,
        "min_distinct_products": 1,
        "min_distinct_brands": 0,
        "min_top_problem_support_rows": 1,
        **profile.get("source_quota", {}),
        **profile.get("research_config", {}).get("source_quota", {}),
    }


def reject_rules(profile: dict) -> dict[str, bool]:
    return {
        "reject_if_media_only": True,
        "reject_if_no_user_problem": True,
        "reject_if_generic_praise_only": True,
        **profile.get("reject_rules", {}),
        **profile.get("research_config", {}).get("reject_rules", {}),
    }


def dimension_label(profile: dict, name: str) -> str:
    labels = profile.get("dimension_labels_zh", {})
    return labels.get(name) or DIMENSION_LABELS_ZH.get(name, name)


def improvement_direction(profile: dict, name: str) -> str:
    zh_rules = profile.get("improvement_rules_zh", {})
    return zh_rules.get(name) or profile.get("improvement_rules", {}).get(name, "转人工复核。")


def listing_guardrail(profile: dict, name: str) -> str:
    rules = profile.get("listing_guardrails_zh", {})
    return rules.get(name, f"不要夸大 {dimension_label(profile, name)}，先用用户问题和测试数据校准卖点。")


def validation_test(profile: dict, name: str) -> str:
    tests = profile.get("supplier_tests_zh", {})
    return tests.get(name, improvement_direction(profile, name))


def source_type_label(value: str) -> str:
    return SOURCE_TYPE_LABELS_ZH.get(normalize(value), value)


def csv_safe(value: object) -> object:
    """Prevent spreadsheet formula execution when CSVs are opened manually."""
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if stripped.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + value
    return value


def safe_href(value: str) -> str:
    low = normalize(value)
    if low.startswith(("http://", "https://")):
        return value
    return "#"


def severity_label(value: str) -> str:
    return SEVERITY_LABELS_ZH.get(normalize(value) or "unknown", value or "未知")


def frequency_label(value: str) -> str:
    return FREQUENCY_LABELS_ZH.get(normalize(value) or "unknown", value or "未知")


def split_dimensions(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,/|]", value or "") if item.strip()]


def parse_int(value: object) -> int:
    if value is None:
        return 0
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else 0


def computed_frequency_signal(row: dict[str, str], support_count: int = 0) -> str:
    evidence_count = parse_int(row.get("evidence_count"))
    frequency_count = parse_int(row.get("frequency_count"))
    product_count = parse_int(row.get("product_count"))
    platform_count = parse_int(row.get("platform_count"))
    count = max(evidence_count, frequency_count, support_count)
    if count >= 8 or product_count >= 3 or platform_count >= 2:
        return "many"
    if count >= 3:
        return "repeated"
    if count >= 1:
        return "single"
    return "unknown"


def is_search_url(value: str) -> bool:
    parsed = urlparse(value or "")
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parse_qs(parsed.query)
    if not host:
        return False
    path_segments = [segment for segment in path.strip("/").split("/") if segment]
    search_path_terms = {"s", "search", "searchpage", "results", "find", "shop"}
    if any(segment in search_path_terms for segment in path_segments):
        return True
    if any(key in query for key in ("q", "k", "st", "search_query", "keyword")) and not path.strip("/"):
        return True
    return False


def has_concrete_source_url(row: dict[str, str]) -> bool:
    url = row.get("url", "")
    if not url.startswith(("http://", "https://")) or is_search_url(url):
        return False
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return bool(parse_qs(parsed.query).get("v") or path.strip("/"))
    if "tiktok.com" in host:
        return "/video/" in path
    if "reddit.com" in host:
        return "/comments/" in path
    return len(path.strip("/")) > 5


def has_primary_audit_anchor(row: dict[str, str]) -> bool:
    return has_concrete_source_url(row) or bool(row.get("screenshot_path"))


def requires_comment_screenshot(row: dict[str, str]) -> bool:
    return normalize(row.get("source_type", "")) in {"youtube_comment", "tiktok_comment"}


def raw_quote_in_evidence(row: dict[str, str]) -> bool:
    quote = normalize(row.get("raw_user_quote", ""))
    evidence = normalize(row.get("evidence_text", ""))
    return bool(quote and evidence and quote in evidence)


def evidence_strength_grade(row_or_rows) -> str:
    rows = row_or_rows if isinstance(row_or_rows, list) else [row_or_rows]
    user_rows = [row for row in rows if row.get("source_group") == "primary" and row.get("user_problem")]
    if not user_rows:
        return "D"
    evidence_total = max(
        len(user_rows),
        max((parse_int(row.get("evidence_count")) for row in user_rows), default=0),
        max((parse_int(row.get("frequency_count")) for row in user_rows), default=0),
    )
    products = {row.get("product_model") or row.get("product_or_topic") for row in user_rows if row.get("product_model") or row.get("product_or_topic")}
    platforms = {row.get("platform") or row.get("source_name") for row in user_rows if row.get("platform") or row.get("source_name")}
    max_product_count = max((parse_int(row.get("product_count")) for row in user_rows), default=0)
    max_platform_count = max((parse_int(row.get("platform_count")) for row in user_rows), default=0)
    product_total = max(len(products), max_product_count)
    platform_total = max(len(platforms), max_platform_count)
    if platform_total >= 2 and product_total >= 3 and evidence_total >= 8:
        return "A"
    if platform_total >= 1 and product_total >= 2 and evidence_total >= 3:
        return "B"
    if product_total >= 1 and evidence_total >= 3:
        return "C"
    return "D"


def suspicious_reasons(row: dict[str, str]) -> list[str]:
    reasons: list[str] = []
    group = row.get("source_group") or source_group(row, {})
    if row.get("is_search_url") == "True" or is_search_url(row.get("url", "")):
        reasons.append("搜索页 URL")
    if group == "primary" and not row.get("screenshot_path") and (
        requires_comment_screenshot(row) or not has_concrete_source_url(row)
    ):
        reasons.append("无截图")
    if group == "primary" and not row.get("raw_user_quote"):
        reasons.append("无原话")
    if group == "primary" and row.get("quote_verified") == "False":
        reasons.append("原话未在证据文本中出现")
    if group == "primary" and row.get("reported_frequency_signal") in {"repeated", "many"} and not any(
        parse_int(row.get(name)) for name in ("evidence_count", "frequency_count", "product_count", "platform_count")
    ):
        reasons.append("频率手填但无数量")
    if group == "secondary":
        reasons.append("只有媒体背景")
    if normalize(row.get("polarity", "")) == "positive" and not row.get("user_problem"):
        reasons.append("只有泛泛好评")
    if group == "primary" and row.get("has_concrete_source") == "False":
        reasons.append("无具体评论/帖子 URL 或截图")
    return reasons


def localize_reflection_note(note: str) -> str:
    replacements = {
        "Primary user-problem evidence.": "来自真实用户源，且包含可分析的用户问题。",
        "Secondary/background source; cannot be main evidence.": "媒体/背景来源，不能作为主证据。",
        "Missing user_problem field.": "缺少 user_problem 字段。",
        "Missing raw_user_quote field.": "缺少 raw_user_quote 原始用户引语。",
        "raw_user_quote not found in evidence_text.": "raw_user_quote 没有出现在 evidence_text 中。",
        "Search results URL is not concrete evidence.": "搜索结果页 URL 不是具体评论/帖子证据。",
        "Missing concrete source URL or screenshot.": "缺少具体评论/帖子 URL 或截图。",
        "Comment source requires screenshot.": "评论类视频/短视频证据需要截图定位。",
        "Missing source_locator field.": "缺少 source_locator 评论定位信息。",
        "Manual frequency_signal overridden by count rules:": "frequency_signal 已按数量规则重算：",
        "Frequency label has no numeric support.": "频率标签缺少数量字段支撑。",
        "Generic praise only.": "只有泛泛好评，不能支撑选品优化。",
        "Missing public URL or screenshot.": "缺少公开 URL 或截图。",
        "Missing evidence text.": "缺少证据文本。",
        "No source/content category keyword match.": "来源内容没有命中品类核心关键词。",
        "No requested fix or parameter direction.": "缺少用户暗示的修复方向或可转产品参数。",
        "Unsupported source_type:": "不支持的来源类型：",
        "Unexpected polarity value:": "异常 polarity 值：",
        "Unexpected problem_severity:": "异常 problem_severity 值：",
        "Unexpected frequency_signal:": "异常 frequency_signal 值：",
        "Exclude keyword hit:": "命中排除词：",
        "Query contains exclude keyword:": "搜索词包含排除词：",
    }
    for english, chinese in replacements.items():
        note = note.replace(english, chinese)
    return note


def hits(text: str, keywords: list[str]) -> list[str]:
    low = normalize(text)
    return [keyword for keyword in keywords if normalize(keyword) in low]


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames and column not in BACKFILLABLE_COLUMNS]
    if missing:
        raise SystemExit(f"Missing columns in observations CSV: {', '.join(missing)}")
    for row in rows:
        for column in BACKFILLABLE_COLUMNS:
            row.setdefault(column, "")
    return rows


def meaningful_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{3,}", normalize(text))
        if token not in STOPWORDS
    }


def has_generic_only_evidence(row: dict[str, str]) -> bool:
    if row.get("user_problem") or row.get("requested_fix"):
        return False
    tokens = set(re.findall(r"[a-z0-9][a-z0-9-]{2,}", normalize(row.get("evidence_text", ""))))
    if not tokens:
        return False
    return tokens.issubset(GENERIC_TERMS)


def infer_problem_dimensions(row: dict[str, str], profile: dict) -> list[str]:
    explicit = split_dimensions(row.get("problem_dimension", ""))
    if explicit:
        return explicit
    text = " ".join([row.get("user_problem", ""), row.get("evidence_text", ""), row.get("notes", "")])
    inferred: list[str] = []
    for name, words in profile.get("negative_dimensions", {}).items():
        if hits(text, words):
            inferred.append(name)
    return inferred


def source_group(row: dict[str, str], profile: dict) -> str:
    source_type = normalize(row.get("source_type", ""))
    if source_type in primary_source_types(profile):
        return "primary"
    if source_type in secondary_source_types(profile):
        return "secondary"
    return "unsupported"


def classify(row: dict[str, str], profile: dict, dimension_counts=None) -> dict[str, object]:
    group = source_group(row, profile)
    rules = reject_rules(profile)
    source_type = normalize(row.get("source_type", ""))
    problem = row.get("user_problem", "").strip()
    raw_quote = row.get("raw_user_quote", "").strip()
    requested = row.get("requested_fix", "").strip()
    parameter = row.get("parameter_to_verify", "").strip()
    supplier = row.get("supplier_test", "").strip()
    dimensions = infer_problem_dimensions(row, profile)
    severity = normalize(row.get("problem_severity", "")) or "unknown"
    manual_frequency = normalize(row.get("frequency_signal", "")) or "unknown"
    support_count = max((dimension_counts or Counter()).get(dimension, 0) for dimension in dimensions) if dimensions else 0
    frequency = computed_frequency_signal(row, support_count)
    if frequency == "unknown":
        frequency = manual_frequency
    polarity = normalize(row.get("polarity", "")) or "unknown"
    search_url = is_search_url(row.get("url", ""))
    concrete_url = has_concrete_source_url(row)
    primary_anchor = has_primary_audit_anchor(row)
    quote_verified = raw_quote_in_evidence(row)
    source_locator = row.get("source_locator", "").strip()

    content_text = " ".join(
        [
            row.get("title", ""),
            row.get("product_or_topic", ""),
            row.get("evidence_text", ""),
            row.get("raw_user_quote", ""),
            row.get("user_problem", ""),
        ]
    )
    query_text = row.get("query", "")
    content_must_hits = hits(content_text, profile["must_include_keywords"])
    query_must_hits = hits(query_text, profile["must_include_keywords"])
    content_nice_hits = hits(content_text, profile.get("nice_to_have_keywords", []))
    exclude_hits = hits(content_text, profile.get("exclude_keywords", []))
    query_exclude_hits = hits(query_text, profile.get("exclude_keywords", []))

    user_source_score = 20 if group == "primary" else 0
    problem_specificity_score = 0
    if len(problem) >= 30:
        problem_specificity_score = 20
    elif len(problem) >= 12:
        problem_specificity_score = 12
    elif problem:
        problem_specificity_score = 6

    traceability_score = 0
    if primary_anchor and quote_verified:
        traceability_score = 20
    elif primary_anchor and raw_quote:
        traceability_score = 12
    elif primary_anchor or quote_verified:
        traceability_score = 8

    frequency_score = {"many": 20, "repeated": 15, "single": 6, "unknown": 0}.get(frequency, 0)

    actionability_score = 0
    if parameter or supplier or requested:
        actionability_score = 20
    elif any(
        dimension in profile.get("improvement_rules", {})
        or dimension in profile.get("improvement_rules_zh", {})
        or dimension in profile.get("supplier_tests_zh", {})
        for dimension in dimensions
    ):
        actionability_score = 18
    elif dimensions:
        actionability_score = 12

    media_penalty = 35 if group == "secondary" and not problem else 18 if group == "secondary" else 0
    generic_praise_penalty = 20 if polarity == "positive" and not problem and has_generic_only_evidence(row) else 0
    category_mismatch_penalty = 0
    if not content_must_hits:
        category_mismatch_penalty += 15
    category_mismatch_penalty += min(40, len(exclude_hits) * 30 + len(query_exclude_hits) * 10)
    category_mismatch_penalty = min(40, category_mismatch_penalty)

    hallucination_penalty = 0
    if not row.get("url") and not row.get("screenshot_path"):
        hallucination_penalty += 10
    if not row.get("evidence_text"):
        hallucination_penalty += 10
    if group == "primary" and not raw_quote:
        hallucination_penalty += 6
    if group == "primary" and raw_quote and not quote_verified:
        hallucination_penalty += 10
    if group == "primary" and not primary_anchor:
        hallucination_penalty += 10
    if group == "primary" and search_url:
        hallucination_penalty += 8
    if group == "primary" and requires_comment_screenshot(row) and not row.get("screenshot_path"):
        hallucination_penalty += 8
    if group == "primary" and frequency in {"repeated", "many"} and support_count < 3 and not any(
        parse_int(row.get(name)) for name in ("evidence_count", "frequency_count", "product_count", "platform_count")
    ):
        hallucination_penalty += 6
    if group == "unsupported":
        hallucination_penalty += 8
    hallucination_penalty = min(30, hallucination_penalty)

    score = (
        user_source_score
        + problem_specificity_score
        + traceability_score
        + frequency_score
        + actionability_score
        - media_penalty
        - generic_praise_penalty
        - category_mismatch_penalty
        - hallucination_penalty
    )
    score = max(0, min(100, score))

    reflection_notes: list[str] = []
    if group == "primary" and problem:
        reflection_notes.append("Primary user-problem evidence.")
    elif group == "secondary":
        reflection_notes.append("Secondary/background source; cannot be main evidence.")
    if not problem:
        reflection_notes.append("Missing user_problem field.")
    if group == "primary" and not raw_quote:
        reflection_notes.append("Missing raw_user_quote field.")
    if group == "primary" and raw_quote and not quote_verified:
        reflection_notes.append("raw_user_quote not found in evidence_text.")
    if search_url:
        reflection_notes.append("Search results URL is not concrete evidence.")
    if group == "primary" and not primary_anchor:
        reflection_notes.append("Missing concrete source URL or screenshot.")
    if group == "primary" and requires_comment_screenshot(row) and not row.get("screenshot_path"):
        reflection_notes.append("Comment source requires screenshot.")
    if manual_frequency != "unknown" and manual_frequency != frequency:
        reflection_notes.append(f"Manual frequency_signal overridden by count rules: {manual_frequency} -> {frequency}.")
    if group == "primary" and manual_frequency in {"repeated", "many"} and frequency == manual_frequency and support_count < 3 and not any(
        parse_int(row.get(name)) for name in ("evidence_count", "frequency_count", "product_count", "platform_count")
    ):
        reflection_notes.append("Frequency label has no numeric support.")
    if generic_praise_penalty:
        reflection_notes.append("Generic praise only.")
    if not row.get("url") and not row.get("screenshot_path"):
        reflection_notes.append("Missing public URL or screenshot.")
    if not row.get("evidence_text"):
        reflection_notes.append("Missing evidence text.")
    if not content_must_hits:
        reflection_notes.append("No source/content category keyword match.")
    if not requested and not parameter and not supplier and not dimensions:
        reflection_notes.append("No requested fix or parameter direction.")
    if exclude_hits:
        reflection_notes.append(f"Exclude keyword hit: {', '.join(exclude_hits)}.")
    if query_exclude_hits:
        reflection_notes.append(f"Query contains exclude keyword: {', '.join(query_exclude_hits)}.")
    if source_type and source_type not in SUPPORTED_SOURCE_TYPES:
        reflection_notes.append(f"Unsupported source_type: {row.get('source_type')}.")
    if polarity not in VALID_POLARITIES:
        reflection_notes.append(f"Unexpected polarity value: {row.get('polarity')}.")
    if severity not in VALID_SEVERITIES:
        reflection_notes.append(f"Unexpected problem_severity: {row.get('problem_severity')}.")
    if frequency not in VALID_FREQUENCY:
        reflection_notes.append(f"Unexpected frequency_signal: {row.get('frequency_signal')}.")

    forced_reject = False
    if rules.get("reject_if_no_user_problem") and group == "primary" and not problem:
        forced_reject = True
    if rules.get("reject_if_generic_praise_only") and generic_praise_penalty:
        forced_reject = True
    if category_mismatch_penalty >= 30:
        forced_reject = True

    if group == "secondary":
        score = min(score, 59)
        if not forced_reject and content_must_hits and not exclude_hits and not query_exclude_hits:
            score = max(score, 40)

    if group == "primary" and not primary_anchor:
        score = min(score, 79)
    if group == "primary" and not quote_verified:
        score = min(score, 79)
    if group == "primary" and not raw_quote:
        score = min(score, 79)
    if group == "primary" and requires_comment_screenshot(row) and not row.get("screenshot_path"):
        score = min(score, 79)

    if forced_reject:
        status = "reject"
    elif score >= 80:
        status = "strong"
    elif score >= 60:
        status = "review"
    elif score >= 40:
        status = "weak"
    else:
        status = "reject"

    if group == "primary" and problem and status == "strong" and frequency in {"single", "unknown"}:
        status = "review"
    if group == "primary" and problem and status == "strong" and (
        not primary_anchor
        or not raw_quote
        or not quote_verified
        or (requires_comment_screenshot(row) and not row.get("screenshot_path"))
    ):
        status = "review"

    improvement = []
    improvement_zh = []
    for dimension in dimensions:
        direction = profile.get("improvement_rules", {}).get(dimension, requested or "Route to manual review.")
        improvement.append(f"{dimension}: {direction} (supported by {row.get('item_id', 'unknown')})")
        direction_zh = parameter or improvement_direction(profile, dimension)
        if requested and not parameter:
            direction_zh = requested
        improvement_zh.append(
            f"{dimension_label(profile, dimension)}: {direction_zh}（支撑证据 {row.get('item_id', 'unknown')}）"
        )

    reflection_note = " ".join(reflection_notes)

    return {
        "score": score,
        "status": status,
        "status_zh": STATUS_LABELS_ZH.get(status, status),
        "source_group": group,
        "frequency_signal": frequency,
        "reported_frequency_signal": manual_frequency,
        "evidence_strength": evidence_strength_grade({**row, "source_group": group, "user_problem": problem}),
        "has_concrete_source": primary_anchor,
        "is_search_url": search_url,
        "quote_verified": quote_verified,
        "problem_value_score": score,
        "source_score": user_source_score,
        "quote_traceability_score": traceability_score,
        "problem_specificity_score": problem_specificity_score,
        "frequency_score": frequency_score,
        "severity_score": 0,
        "actionability_score": actionability_score,
        "context_score": traceability_score,
        "media_penalty": media_penalty,
        "generic_praise_penalty": generic_praise_penalty,
        "category_mismatch_penalty": category_mismatch_penalty,
        "hallucination_penalty": hallucination_penalty,
        "content_must_hits": "; ".join(content_must_hits),
        "query_must_hits": "; ".join(query_must_hits),
        "nice_hits": "; ".join(content_nice_hits),
        "exclude_hits": "; ".join(exclude_hits),
        "problem_dimensions": "; ".join(dimensions),
        "problem_dimensions_zh": "; ".join(dimension_label(profile, name) for name in dimensions),
        "improvement_direction": " | ".join(improvement),
        "improvement_direction_zh": " | ".join(improvement_zh),
        "reflection_note": reflection_note,
        "reflection_note_zh": localize_reflection_note(reflection_note),
    }


def is_user_problem_row(row: dict[str, str]) -> bool:
    return row.get("source_group") == "primary" and bool(row.get("user_problem")) and row.get("status") != "reject"


def is_negative_or_question(row: dict[str, str]) -> bool:
    return normalize(row.get("polarity", "")) in {"negative", "mixed", "risk", "question"}


def severity_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(normalize(value), 0)


def frequency_rank(value: str) -> int:
    return {"many": 3, "repeated": 2, "single": 1}.get(normalize(value), 0)


def assess_quota(profile: dict, rows: list[dict[str, str]]) -> dict[str, object]:
    quota = source_quota(profile)
    user_rows = [row for row in rows if is_user_problem_row(row)]
    negative_or_question = [row for row in user_rows if is_negative_or_question(row)]
    media_rows = [row for row in rows if row.get("source_group") == "secondary" and row.get("status") != "reject"]
    distinct_user_sources = {row.get("source_name") for row in user_rows if row.get("source_name")}
    distinct_platforms = {
        row.get("platform") or row.get("source_name")
        for row in user_rows
        if row.get("platform") or row.get("source_name")
    }
    distinct_products = {
        row.get("product_model") or row.get("product_or_topic")
        for row in user_rows
        if row.get("product_model") or row.get("product_or_topic")
    }
    distinct_brands = {row.get("brand") for row in user_rows if row.get("brand")}
    dimension_support = Counter()
    for row in user_rows:
        for dimension in [item for item in row.get("problem_dimensions", "").split("; ") if item]:
            dimension_support[dimension] += 1
    top_problem_support_rows = max(dimension_support.values(), default=0)
    accepted_rows = user_rows + media_rows
    media_ratio = len(media_rows) / len(accepted_rows) if accepted_rows else 0.0

    checks = {
        "user_problem_rows": (len(user_rows), quota["min_user_problem_rows"], len(user_rows) >= quota["min_user_problem_rows"]),
        "negative_or_question_rows": (
            len(negative_or_question),
            quota["min_negative_or_question_rows"],
            len(negative_or_question) >= quota["min_negative_or_question_rows"],
        ),
        "media_rows": (len(media_rows), quota["max_media_rows"], len(media_rows) <= quota["max_media_rows"]),
        "media_ratio": (
            f"{media_ratio:.0%}",
            f"{quota['max_media_ratio']:.0%}",
            media_ratio <= quota["max_media_ratio"],
        ),
        "distinct_user_sources": (
            len(distinct_user_sources),
            quota["min_distinct_user_sources"],
            len(distinct_user_sources) >= quota["min_distinct_user_sources"],
        ),
        "distinct_platforms": (
            len(distinct_platforms),
            quota["min_distinct_platforms"],
            len(distinct_platforms) >= quota["min_distinct_platforms"],
        ),
        "distinct_products": (
            len(distinct_products),
            quota["min_distinct_products"],
            len(distinct_products) >= quota["min_distinct_products"],
        ),
        "distinct_brands": (
            len(distinct_brands),
            quota["min_distinct_brands"],
            len(distinct_brands) >= quota["min_distinct_brands"],
        ),
        "top_problem_support_rows": (
            top_problem_support_rows,
            quota["min_top_problem_support_rows"],
            top_problem_support_rows >= quota["min_top_problem_support_rows"],
        ),
    }
    media_only = not user_rows and bool(media_rows)
    passed = all(item[2] for item in checks.values())
    if reject_rules(profile).get("reject_if_media_only") and media_only:
        passed = False
    return {"passed": passed, "media_only": media_only, "checks": checks}


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else REQUIRED_COLUMNS
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_safe(value) for key, value in row.items()})


def write_chinese_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "证据ID",
        "搜索词",
        "平台",
        "品牌",
        "型号",
        "来源类型",
        "来源分组",
        "来源名称",
        "评论评分",
        "评论日期",
        "评论数信号",
        "证据定位",
        "标题",
        "产品/主题",
        "证据原文",
        "用户原话",
        "用户问题",
        "问题维度",
        "严重度",
        "重复信号",
        "人工频率标签",
        "证据条数",
        "同类问题次数",
        "涉及商品数",
        "涉及平台数",
        "频率证据",
        "用户想要的修复",
        "待验证参数",
        "供应商测试项",
        "倾向",
        "痛点价值分",
        "证据强度",
        "具体证据",
        "原话可验证",
        "状态",
        "真实用户源分",
        "原话可追溯分",
        "问题具体度分",
        "重复信号分",
        "严重度分",
        "可行动参数分",
        "上下文完整分",
        "媒体惩罚",
        "泛泛好评惩罚",
        "品类错配惩罚",
        "幻觉风险惩罚",
        "改进方向",
        "反思结论",
        "URL",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output_row = {
                "证据ID": row.get("item_id", ""),
                "搜索词": row.get("query", ""),
                "平台": row.get("platform", ""),
                "品牌": row.get("brand", ""),
                "型号": row.get("product_model", ""),
                "来源类型": source_type_label(row.get("source_type", "")),
                "来源分组": "真实用户源" if row.get("source_group") == "primary" else "背景来源",
                "来源名称": row.get("source_name", ""),
                "评论评分": row.get("review_rating", ""),
                "评论日期": row.get("review_date", ""),
                "评论数信号": row.get("review_count_signal", ""),
                "证据定位": row.get("source_locator", ""),
                "标题": row.get("title", ""),
                "产品/主题": row.get("product_or_topic", ""),
                "证据原文": row.get("evidence_text", ""),
                "用户原话": row.get("raw_user_quote", ""),
                "用户问题": row.get("user_problem", ""),
                "问题维度": row.get("problem_dimensions_zh", ""),
                "严重度": severity_label(row.get("problem_severity", "")),
                "重复信号": frequency_label(row.get("frequency_signal", "")),
                "人工频率标签": frequency_label(row.get("reported_frequency_signal", "")),
                "证据条数": row.get("evidence_count", ""),
                "同类问题次数": row.get("frequency_count", ""),
                "涉及商品数": row.get("product_count", ""),
                "涉及平台数": row.get("platform_count", ""),
                "频率证据": row.get("frequency_evidence", ""),
                "用户想要的修复": row.get("requested_fix", ""),
                "待验证参数": row.get("parameter_to_verify", ""),
                "供应商测试项": row.get("supplier_test", ""),
                "倾向": row.get("polarity", ""),
                "痛点价值分": row.get("problem_value_score", row.get("score", "")),
                "证据强度": row.get("evidence_strength", ""),
                "具体证据": "是" if row.get("has_concrete_source") == "True" else "否",
                "原话可验证": "是" if row.get("quote_verified") == "True" else "否",
                "状态": row.get("status_zh", row.get("status", "")),
                "真实用户源分": row.get("source_score", ""),
                "原话可追溯分": row.get("quote_traceability_score", ""),
                "问题具体度分": row.get("problem_specificity_score", ""),
                "重复信号分": row.get("frequency_score", ""),
                "严重度分": row.get("severity_score", ""),
                "可行动参数分": row.get("actionability_score", ""),
                "上下文完整分": row.get("context_score", ""),
                "媒体惩罚": row.get("media_penalty", ""),
                "泛泛好评惩罚": row.get("generic_praise_penalty", ""),
                "品类错配惩罚": row.get("category_mismatch_penalty", ""),
                "幻觉风险惩罚": row.get("hallucination_penalty", ""),
                "改进方向": row.get("improvement_direction_zh", ""),
                "反思结论": row.get("reflection_note_zh", ""),
                "URL": row.get("url", ""),
            }
            writer.writerow({key: csv_safe(value) for key, value in output_row.items()})


def rows_for_dimension(rows: list[dict[str, str]], dimension: str) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if dimension in [item for item in row.get("problem_dimensions", "").split("; ") if item]
        and row.get("status") != "reject"
    ]


def first_nonempty(values: list[str], fallback: str = "") -> str:
    for value in values:
        if value:
            return value
    return fallback


def summarize_dimensions(profile: dict, user_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    dimensions = Counter()
    for row in user_rows:
        for dimension in [item for item in row.get("problem_dimensions", "").split("; ") if item]:
            dimensions[dimension] += 1

    summaries: list[dict[str, object]] = []
    for dimension, count in dimensions.items():
        support = rows_for_dimension(user_rows, dimension)
        support = sorted(
            support,
            key=lambda row: (
                frequency_rank(row.get("frequency_signal", "")),
                severity_rank(row.get("problem_severity", "")),
                int(row.get("score", 0)),
            ),
            reverse=True,
        )
        sources = sorted({row.get("source_name", "") for row in support if row.get("source_name", "")})
        platforms = sorted(
            {
                row.get("platform") or row.get("source_name", "")
                for row in support
                if row.get("platform") or row.get("source_name")
            }
        )
        brands = sorted({row.get("brand", "") for row in support if row.get("brand", "")})
        products = sorted(
            {
                row.get("product_model") or row.get("product_or_topic", "")
                for row in support
                if row.get("product_model") or row.get("product_or_topic")
            }
        )
        evidence_total = max(
            len(support),
            max((parse_int(row.get("evidence_count")) for row in support), default=0),
            max((parse_int(row.get("frequency_count")) for row in support), default=0),
        )
        top_row = support[0]
        summaries.append(
            {
                "dimension": dimension,
                "label": dimension_label(profile, dimension),
                "count": count,
                "evidence_total": evidence_total,
                "support_ids": ", ".join(row["item_id"] for row in support),
                "sources": ", ".join(sources),
                "platforms": ", ".join(platforms),
                "brands": ", ".join(brands),
                "products": ", ".join(products),
                "severity": max((row.get("problem_severity", "unknown") for row in support), key=severity_rank),
                "frequency": max((row.get("frequency_signal", "unknown") for row in support), key=frequency_rank),
                "frequency_evidence": first_nonempty([row.get("frequency_evidence", "") for row in support]),
                "evidence_strength": evidence_strength_grade(support),
                "raw_user_quote": first_nonempty([row.get("raw_user_quote", "") for row in support]),
                "user_problem": top_row.get("user_problem", ""),
                "parameter_to_verify": first_nonempty(
                    [row.get("parameter_to_verify", "") for row in support],
                    improvement_direction(profile, dimension),
                ),
                "supplier_test": first_nonempty(
                    [row.get("supplier_test", "") for row in support],
                    validation_test(profile, dimension),
                ),
                "listing_guardrail": listing_guardrail(profile, dimension),
                "improvement": improvement_direction(profile, dimension),
                "score": max(int(row.get("score", 0)) for row in support),
            }
        )
    return sorted(
        summaries,
        key=lambda item: (
            int(item["count"]),
            int(item["evidence_total"]),
            frequency_rank(str(item["frequency"])),
            severity_rank(str(item["severity"])),
            int(item["score"]),
        ),
        reverse=True,
    )


def build_report(profile: dict, rows: list[dict[str, str]]) -> str:
    quota = assess_quota(profile, rows)
    status_counts = Counter(row["status"] for row in rows)
    user_rows = [row for row in rows if is_user_problem_row(row)]
    media_rows = [row for row in rows if row.get("source_group") == "secondary" and row.get("status") != "reject"]
    dimension_summaries = summarize_dimensions(profile, user_rows)

    conclusion = "通过用户问题初筛" if quota["passed"] else "不通过，需要补采真实用户问题证据"
    lines = [
        f"# {display_name(profile)} 用户问题驱动选品审查报告",
        "",
        f"- 搜索需求：{search_need(profile)}",
        f"- 审查结论：{conclusion}",
        f"- 强用户问题证据：{status_counts['strong']}",
        f"- 待人工复核：{status_counts['review']}",
        f"- 弱匹配/背景：{status_counts['weak']}",
        f"- 剔除/跑题：{status_counts['reject']}",
        "",
        "## 采集配额审查",
        "",
        "| 指标 | 当前 | 要求 | 结果 |",
        "|---|---:|---:|---|",
    ]
    labels = {
        "user_problem_rows": "真实用户问题行",
        "negative_or_question_rows": "负向/疑问行",
        "media_rows": "媒体背景行上限",
        "distinct_user_sources": "不同用户来源数",
        "media_ratio": "媒体背景占比上限",
        "distinct_platforms": "不同平台数",
        "distinct_products": "不同商品/型号数",
        "distinct_brands": "不同品牌数",
        "top_problem_support_rows": "Top 痛点支撑行数",
    }
    for name, (actual, expected, passed) in quota["checks"].items():
        lines.append(f"| {labels[name]} | {actual} | {expected} | {'通过' if passed else '不通过'} |")
    if quota["media_only"]:
        lines.append("")
        lines.append("> 当前数据只有媒体/背景来源，没有足够真实用户问题，不能作为选品优化主证据。")

    lines.extend(["", "## 用户真实问题 Top 10", ""])
    top_rows = sorted(
        user_rows,
        key=lambda row: (
            frequency_rank(row.get("frequency_signal", "")),
            severity_rank(row.get("problem_severity", "")),
            int(row.get("score", 0)),
        ),
        reverse=True,
    )[:10]
    if top_rows:
        lines.extend(
            [
                "| 排名 | ID | 来源 | 问题维度 | 重复信号 | 用户原话 | 用户问题 |",
                "|---:|---|---|---|---|---|---|",
            ]
        )
        for index, row in enumerate(top_rows, start=1):
            lines.append(
                f"| {index} | {row['item_id']} | {source_type_label(row['source_type'])} | "
                f"{row.get('problem_dimensions_zh', '')} | {frequency_label(row.get('frequency_signal', ''))} | "
                f"{row.get('raw_user_quote', '')} | {row.get('user_problem', '')} |"
            )
    else:
        lines.append("- 暂无合格的真实用户问题证据。")

    lines.extend(["", "## 高频问题簇", ""])
    if dimension_summaries:
        lines.extend(
            [
                "| 问题簇 | 证据强度 | 证据行 | 证据条数 | 频率 | 支撑证据 | 用户原话样例 |",
                "|---|---|---:|---:|---|---|---|",
            ]
        )
        for item in dimension_summaries:
            lines.append(
                f"| {item['label']}（{item['dimension']}） | {item['evidence_strength']} | {item['count']} | "
                f"{item['evidence_total']} | {frequency_label(str(item['frequency']))} | "
                f"{item['support_ids']} | {item['raw_user_quote']} |"
            )
    else:
        lines.append("- 暂无足够用户差评点，不能判断高频问题。")

    lines.extend(["", "## 产品参数/供应商测试", ""])
    if dimension_summaries:
        lines.extend(["| 问题簇 | evidence_ids | frequency | parameter_to_verify | supplier_test |", "|---|---|---|---|---|"])
        for item in dimension_summaries:
            lines.append(
                f"| {item['label']} | {item['support_ids']} | {frequency_label(str(item['frequency']))} | "
                f"{item['parameter_to_verify']} | {item['supplier_test']} |"
            )
    else:
        lines.append("- 需要先补采真实用户问题，再沉淀产品参数和供应商测试。")

    suspicious_rows = [(row, suspicious_reasons(row)) for row in rows]
    suspicious_rows = [(row, reasons) for row, reasons in suspicious_rows if reasons]
    lines.extend(["", "## 可疑证据队列", ""])
    if suspicious_rows:
        lines.extend(["| ID | 来源 | 状态 | 可疑原因 | 处理建议 |", "|---|---|---|---|---|"])
        for row, reasons in suspicious_rows:
            action = "补具体评论/帖子 URL 或截图后复核" if row.get("source_group") == "primary" else "仅保留为背景，不进入主证据"
            lines.append(
                f"| {row['item_id']} | {source_type_label(row['source_type'])} · {row.get('source_name', '')} | "
                f"{row.get('status_zh', row.get('status', ''))} | {', '.join(reasons)} | {action} |"
            )
    else:
        lines.append("- 暂无可疑证据。")
    review_count = status_counts["review"]
    if review_count:
        lines.extend(
            [
                "",
                f"待人工复核证据共有 {review_count} 条。常见原因是有真实用户问题，但重复证据、跨产品/平台支撑、截图或原话可见性还不足。",
            ]
        )
    lines.extend(
        [
            "",
            "人工复核前请确认：URL 是否能打开到具体评论/问答/帖子；raw_user_quote 是否原文可见；user_problem 是否忠实于原文；problem_dimension 是否适合该品类；供应商测试是否能实际执行；Listing guardrail 是否避免过度承诺。",
        ]
    )
    return "\n".join(lines)


def build_dashboard(profile: dict, rows: list[dict[str, str]]) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value), quote=True)

    quota = assess_quota(profile, rows)
    user_rows = [row for row in rows if is_user_problem_row(row)]
    repeated_rows = [
        row
        for row in user_rows
        if normalize(row.get("frequency_signal", "")) in {"repeated", "many"}
    ]
    media_rows = [row for row in rows if row.get("source_group") == "secondary" and row.get("status") != "reject"]
    reject_rows = [row for row in rows if row.get("status") == "reject"]

    row_cards = []
    for row in sorted(rows, key=lambda item: int(item["score"]), reverse=True):
        problem = row.get("user_problem") or "未提取真实用户问题"
        source_badge = "真实用户源" if row.get("source_group") == "primary" else "媒体/背景"
        row_cards.append(
            f"""
            <article class="row-card {esc(row['status'])}">
              <div class="row-head"><strong>{esc(row['item_id'])} · {esc(source_badge)}</strong><span>{esc(row.get('problem_value_score', row['score']))}/100 · {esc(row['status_zh'])}</span></div>
              <h3>{esc(problem)}</h3>
              <p class="quote">{esc(row.get('raw_user_quote') or '无用户原话，不能作为主证据')}</p>
              <dl>
                <div><dt>频率</dt><dd>{esc(frequency_label(row.get('frequency_signal', '')))} · {esc(row.get('frequency_evidence') or '未记录频率证据')}</dd></div>
                <div><dt>问题维度</dt><dd>{esc(row.get('problem_dimensions_zh') or row.get('problem_dimension') or '待复核')}</dd></div>
                <div><dt>可追溯</dt><dd>{esc('通过' if row.get('has_concrete_source') == 'True' and row.get('quote_verified') == 'True' else '待补强')}</dd></div>
              </dl>
              <small>{esc(source_type_label(row['source_type']))} · {esc(row['source_name'])} · <a href="{esc(safe_href(row.get('url', '')))}">{esc(row.get('url', ''))}</a></small>
              <div class="reflection">{esc(row['reflection_note_zh'])}</div>
            </article>
            """
        )

    css = """
    body { margin: 0; background: #f5f7f3; color: #17201d; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; }
    main { max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }
    .hero, .row-card { background: #fff; border: 1px solid #dfe5dc; border-radius: 8px; box-shadow: 0 14px 36px rgba(20, 30, 25, .07); }
    .hero { padding: 26px; margin-bottom: 18px; }
    h1 { margin: 0 0 10px; font-size: 32px; letter-spacing: 0; }
    p { color: #63706b; line-height: 1.55; }
    .status { display: inline-block; margin-top: 8px; padding: 8px 10px; border-radius: 8px; background: #f3f6f1; color: #384541; font-size: 13px; }
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 20px; }
    .kpi { border: 1px solid #dfe5dc; border-radius: 8px; padding: 14px; background: #fbfcfa; }
    .kpi span { display: block; color: #63706b; font-size: 12px; }
    .kpi strong { display: block; font-size: 24px; margin-top: 5px; }
    .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
    .row-card { padding: 16px; }
    .row-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
    .row-head span { border-radius: 999px; padding: 4px 8px; font-size: 12px; background: #eef4ef; color: #0f8b76; }
    .reject .row-head span { background: #f7e9e5; color: #a64e3d; }
    .weak .row-head span { background: #f7f1df; color: #916b18; }
    h3 { margin: 12px 0 6px; font-size: 16px; }
    .quote { margin: 8px 0; color: #293631; font-style: italic; }
    dl { display: grid; gap: 8px; margin: 12px 0; }
    dl div { border-left: 3px solid #cbd8ce; padding-left: 9px; }
    dt { color: #63706b; font-size: 12px; }
    dd { margin: 2px 0 0; color: #293631; line-height: 1.45; }
    small, a { color: #63706b; word-break: break-all; }
    .reflection { margin-top: 12px; border-radius: 8px; padding: 10px; background: #f3f6f1; color: #384541; font-size: 13px; }
    @media (max-width: 800px) { .kpis, .grid { grid-template-columns: 1fr; } }
    """
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(display_name(profile))} 用户问题选品审查</title>
  <style>{css}</style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>{esc(display_name(profile))} 用户问题选品审查</h1>
      <p>{esc(search_need(profile))}</p>
      <div class="status">审查结论：{esc('通过用户问题初筛' if quota['passed'] else '不通过，需要补采真实用户问题证据')}</div>
      <div class="kpis">
        <div class="kpi"><span>真实用户问题</span><strong>{len(user_rows)}</strong></div>
        <div class="kpi"><span>重复问题</span><strong>{len(repeated_rows)}</strong></div>
        <div class="kpi"><span>媒体背景</span><strong>{len(media_rows)}</strong></div>
        <div class="kpi"><span>剔除/跑题</span><strong>{len(reject_rows)}</strong></div>
      </div>
    </section>
    <section class="grid">{''.join(row_cards)}</section>
  </main>
</body>
</html>"""


def run(profile_path: Path, observations_path: Path, out_dir: Path) -> None:
    profile = read_json(profile_path)
    rows = read_rows(observations_path)
    dimension_counts = Counter()
    for row in rows:
        if source_group(row, profile) == "primary" and row.get("user_problem"):
            for dimension in infer_problem_dimensions(row, profile):
                dimension_counts[dimension] += 1
    scored_rows: list[dict[str, str]] = []
    for row in rows:
        result = classify(row, profile, dimension_counts)
        scored_rows.append({**row, **{key: str(value) for key, value in result.items()}})

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "scored_observations.csv", scored_rows)
    write_chinese_csv(out_dir / "scored_observations_zh.csv", scored_rows)
    (out_dir / "reflection_report.md").write_text(build_report(profile, scored_rows), encoding="utf-8")
    (out_dir / "dashboard.html").write_text(build_dashboard(profile, scored_rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score category scouting observations with user-problem-first checks.")
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    run(args.profile, args.observations, args.out)
    print(f"Wrote category scout outputs to {args.out}")


if __name__ == "__main__":
    main()
