from datetime import datetime, timedelta


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


def filter_items(items, days=14, mode="practical"):
    """
    AI资讯过滤层

    Args:
        items:
            RawItem列表

        days:
            最近多少天资讯

        mode:
            strict:
                没有日期直接丢弃

            practical:
                没有日期保留但降权
    """

    seen = set()
    result = []

    cutoff_date = datetime.now() - timedelta(days=days)


    for item in items:

        # 标题为空
        if not item.title:
            continue


        title = item.title.strip()


        # 标题过短
        if len(title) < 5:
            continue


        # URL去重
        if item.url in seen:
            continue

        seen.add(item.url)



        # --------------------
        # 来源评分
        # --------------------

        score = SOURCE_WEIGHT.get(
            item.source,
            3
        )


        for kw in KEYWORDS:

            if kw.lower() in title.lower():
                score += 2



        # --------------------
        # 日期过滤
        # --------------------

        has_date = False
        is_within_range = False


        if item.published_at:

            try:

                pub_date = datetime.strptime(
                    item.published_at,
                    "%Y-%m-%d"
                )

                has_date = True


                if pub_date >= cutoff_date:
                    is_within_range = True


            except (
                ValueError,
                TypeError
            ):
                pass



        if has_date:

            # 超过时间范围
            if not is_within_range:
                continue


        else:

            # 没日期
            if mode == "strict":

                continue

            else:

                # 实用模式降权
                score -= 3



        item.extra = item.extra or {}

        item.extra["score"] = score


        result.append(item)



    # --------------------
    # 总排序
    # --------------------

    result.sort(
        key=lambda x: x.extra.get(
            "score",
            0
        ),
        reverse=True
    )



    # --------------------
    # 国内源保底
    # --------------------

    per_source_limit = 5

    picked_domestic = []

    seen_urls = set()



    for source in DOMESTIC_SOURCES:

        source_items = [
            x for x in result
            if x.source == source
        ]


        for item in source_items[:per_source_limit]:

            if item.url not in seen_urls:

                picked_domestic.append(item)

                seen_urls.add(item.url)



    # --------------------
    # 海外源补足
    # --------------------

    overseas = [
        x for x in result
        if x.source not in DOMESTIC_SOURCES
    ]


    picked_overseas = [
        x for x in overseas
        if x.url not in seen_urls
    ][
        :max(
            0,
            45 - len(picked_domestic)
        )
    ]



    merged = (
        picked_domestic
        +
        picked_overseas
    )



    merged.sort(
        key=lambda x: x.extra.get(
            "score",
            0
        ),
        reverse=True
    )


    return merged[:45]