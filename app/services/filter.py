DOMESTIC_SOURCES = {
    "AI工具集",
    "AIbase",
    "XixAI",
}

SOURCE_WEIGHT = {
    "OpenAI": 10,
    "Anthropic": 10,
    "HuggingFace": 9,
    "Google Research": 9,
    "TechCrunch": 8,
    "VentureBeat": 8,
    "AI工具集": 10,
    "AIbase": 10,
    "XixAI": 9,
    "Reddit": 5,
    "GitHub": 6,
}

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


def filter_items(items):
    """AI资讯过滤层：去重、评分、国内源保底。"""
    seen = set()
    result = []

    for item in items:
        if not item.title:
            continue

        title = item.title.strip()
        if len(title) < 5:
            continue

        if item.url in seen:
            continue
        seen.add(item.url)

        score = SOURCE_WEIGHT.get(item.source, 3)
        for kw in KEYWORDS:
            if kw.lower() in title.lower():
                score += 2

        item.extra = item.extra or {}
        item.extra["score"] = score
        result.append(item)

    result.sort(key=lambda x: x.extra.get("score", 0), reverse=True)

    per_source_limit = 5
    picked_domestic: list = []
    seen_urls: set = set()
    for source in DOMESTIC_SOURCES:
        source_items = [x for x in result if x.source == source]
        for item in source_items[:per_source_limit]:
            if item.url not in seen_urls:
                picked_domestic.append(item)
                seen_urls.add(item.url)

    overseas = [x for x in result if x.source not in DOMESTIC_SOURCES]
    picked_overseas = [x for x in overseas if x.url not in seen_urls][
        : max(0, 45 - len(picked_domestic))
    ]
    merged = picked_domestic + picked_overseas
    merged.sort(key=lambda x: x.extra.get("score", 0), reverse=True)
    return merged[:45]
