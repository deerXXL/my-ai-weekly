def filter_items(items):
    """
    基础数据过滤 + 去重
    """

    seen = set()
    result = []

    for item in items:

        if not item.title:
            continue

        if len(item.title.strip()) < 5:
            continue

        if item.url in seen:
            continue

        seen.add(item.url)
        result.append(item)

    return result