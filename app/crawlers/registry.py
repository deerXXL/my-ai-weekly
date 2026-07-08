from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.openai_blog import fetch_openai_blog
from app.crawlers.huggingface_blog import fetch_huggingface_blog
from app.crawlers.google_research import fetch_google_research
from app.crawlers.techcrunch_ai import fetch_techcrunch_ai
from app.crawlers.techcrunch_ai import fetch_techcrunch_ai
from app.crawlers.venturebeat_ai import fetch_venturebeat_ai
from app.crawlers.jiqizhixin_ai import fetch_jiqizhixin
from app.crawlers.kr36_ai import fetch_36kr_ai
from app.crawlers.reddit_ml import fetch_reddit_ml

def load_all_sources():
    """
    统一加载所有数据源
    """

    items = []

    sources = [
        fetch_github_trending,
        fetch_openai_blog,
        fetch_huggingface_blog,
        fetch_google_research,
        fetch_techcrunch_ai,
        fetch_venturebeat_ai,
        fetch_jiqizhixin,
        fetch_36kr_ai,
        fetch_reddit_ml
    ]

    for source in sources:
        try:
            items.extend(source())
        except Exception as e:
            print("❌ source error:", source.__name__, e)

    return items
