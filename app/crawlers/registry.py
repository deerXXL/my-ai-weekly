from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.openai_blog import fetch_openai_blog
from app.crawlers.anthropic_blog import fetch_anthropic_blog
from app.crawlers.huggingface_blog import fetch_huggingface_blog
from app.crawlers.google_research import fetch_google_research
from app.crawlers.techcrunch_ai import fetch_techcrunch_ai
from app.crawlers.venturebeat_ai import fetch_venturebeat_ai
from app.crawlers.jiqizhixin_ai import fetch_jiqizhixin
from app.crawlers.kr36_ai import fetch_36kr_ai
from app.crawlers.reddit_ml import fetch_reddit_ml

# 双周报告需要覆盖14天的内容，所有crawler提高抓取量
BIWEEKLY_LIMIT = 40

def load_all_sources():
    """
    统一加载所有数据源（双周模式：每个源抓取40条，保证14天覆盖）
    """

    items = []

    sources = [
        (fetch_github_trending, {}),
        (fetch_openai_blog, {"limit": BIWEEKLY_LIMIT}),
        (fetch_anthropic_blog, {"limit": BIWEEKLY_LIMIT}),
        (fetch_huggingface_blog, {"limit": BIWEEKLY_LIMIT}),
        (fetch_google_research, {}),
        (fetch_techcrunch_ai, {"limit": BIWEEKLY_LIMIT}),
        (fetch_venturebeat_ai, {"limit": BIWEEKLY_LIMIT}),
        (fetch_jiqizhixin, {}),
        (fetch_36kr_ai, {}),
        (fetch_reddit_ml, {}),
    ]

    for source, kwargs in sources:
        try:
            items.extend(source(**kwargs))
        except Exception as e:
            print("❌ source error:", source.__name__, e)

    return items
