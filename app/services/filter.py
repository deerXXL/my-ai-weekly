from datetime import datetime, timedelta


def filter_items(items, days=14, mode="practical"):
    """
    AI资讯过滤层
    
    Args:
        items: RawItem列表
        days: 最近N天内的资讯（默认14天）
        mode: 日期过滤模式
              - "strict": 保守模式，没有日期的直接丢弃
              - "practical": 实用模式，没有日期的保留但降权（默认）
    """

    seen = set()
    result = []

    # 来源权重
    source_weight = {

    "OpenAI":10,

    "Anthropic":10,

    "HuggingFace":9,

    "Google Research":9,


    "TechCrunch":8,

    "VentureBeat":8,


    "机器之心":7,

    "36氪":7,


    "Reddit":5,


    "GitHub":6,

}


    keywords = [

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
        "智能体"

    ]

    cutoff_date = datetime.now() - timedelta(days=days)

    for item in items:

        # 标题为空
        if not item.title:
            continue


        title = item.title.strip()


        if len(title) < 5:
            continue


        # URL去重
        if item.url in seen:
            continue

        seen.add(item.url)



        # 计算相关性

        score = 0


        # 来源评分

        score += source_weight.get(
            item.source,
            3
        )


        # 标题关键词

        for kw in keywords:

            if kw.lower() in title.lower():

                score += 2


        # 日期过滤（实用模式）
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
            if is_within_range:
                # 日期在范围内，正常保留
                pass
            else:
                # 日期超期，直接丢弃
                continue
        else:
            # 没有日期
            if mode == "strict":
                # 保守模式：没有日期直接丢弃
                continue
            else:
                # 实用模式：保留但降权，避免漏掉重要新闻
                score -= 3

        item.extra = item.extra or {}

        item.extra["score"] = score


        result.append(item)



    # 高质量排序

    result.sort(

        key=lambda x:
        x.extra.get(
            "score",
            0
        ),

        reverse=True

    )


    # 保留前30条最有价值的资讯
    return result[:30]