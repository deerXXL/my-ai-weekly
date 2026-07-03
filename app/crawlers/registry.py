from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.openai_blog import fetch_openai_blog
from app.crawlers.huggingface_blog import fetch_huggingface_blog


def load_all_sources():
    """
    统一加载所有数据源
    """

    items = []

    sources = [
        fetch_github_trending,
        fetch_openai_blog,
        fetch_huggingface_blog,
        fetch_huggingface_blog,
    ]

    for source in sources:
        try:
            items.extend(source())
        except Exception as e:
            print("❌ source error:", source.__name__, e)

    return items