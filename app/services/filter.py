def filter_items(items):
    """
    AI资讯过滤层
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


    # 保留前30

    return result[:30]