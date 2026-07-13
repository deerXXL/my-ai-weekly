"""资讯过滤、去重与优先级排序（国内源优先）。"""
import re
from datetime import datetime, timedelta

from app.services.sources_config import (
    domestic_source_names,
    load_sources_config,
    source_weights,
)

KEYWORDS = [
    "AI",
    "LLM",
    "Agent",
    "模型",
    "GPT",
    "Claude",
    "Gemma",
    "机器人",
    "多模态",
    "大模型",
    "智能体",
]


def _normalize_title(title: str) -> str:
    """标题归一化，用于跨源去重。"""
    text = title.lower().strip()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text[:80]


def filter_items(items, days=14, mode="practical"):
    """
    去重 + 时间过滤 + 评分排序 + 国内源保底。
    """
    cfg = load_sources_config()
    domestic = domestic_source_names()
    weights = source_weights()
    per_source_min = int(cfg.get("domestic_per_source_min", 5))
    total_cap = int(cfg.get("total_after_filter", 45))

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    result = []
    cutoff_date = datetime.now() - timedelta(days=days)

    for item in items:
        if not item.title:
            continue

        title = item.title.strip()
        if len(title) < 5:
            continue

        if item.url in seen_urls:
            continue

        norm_title = _normalize_title(title)
        if norm_title and norm_title in seen_titles:
            continue

        seen_urls.add(item.url)
        if norm_title:
            seen_titles.add(norm_title)

        score = weights.get(item.source, 3)
        if item.source in domestic:
            score += 3  # 国内源额外加权

        for kw in KEYWORDS:
            if kw.lower() in title.lower():
                score += 2

        has_date = False
        is_within_range = False

        if item.published_at:
            try:
                pub_date = datetime.strptime(item.published_at, "%Y-%m-%d")
                has_date = True
                if pub_date >= cutoff_date:
                    is_within_range = True
            except (ValueError, TypeError):
                pass

        if has_date:
            if not is_within_range:
                continue
        elif mode == "strict":
            continue
        else:
            score -= 3

        item.extra = item.extra or {}
        item.extra["score"] = score
        result.append(item)

    result.sort(key=lambda x: x.extra.get("score", 0), reverse=True)

    picked_domestic = []
    picked_urls: set[str] = set()

    for source in domestic:
        source_items = [x for x in result if x.source == source]
        for item in source_items[:per_source_min]:
            if item.url not in picked_urls:
                picked_domestic.append(item)
                picked_urls.add(item.url)

    overseas = [x for x in result if x.source not in domestic]
    picked_overseas = [
        x for x in overseas if x.url not in picked_urls
    ][: max(0, total_cap - len(picked_domestic))]

    merged = picked_domestic + picked_overseas
    merged.sort(key=lambda x: x.extra.get("score", 0), reverse=True)
    return merged[:total_cap]
