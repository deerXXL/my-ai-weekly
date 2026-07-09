from concurrent.futures import ThreadPoolExecutor, as_completed

from app.crawlers.ai_bot_daily import fetch_ai_bot_daily
from app.crawlers.aibase_news import fetch_aibase_news
from app.crawlers.xix_ai_news import fetch_xix_ai_news
from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.openai_blog import fetch_openai_blog
from app.crawlers.huggingface_blog import fetch_huggingface_blog
from app.crawlers.google_research import fetch_google_research
from app.crawlers.techcrunch_ai import fetch_techcrunch_ai
from app.crawlers.venturebeat_ai import fetch_venturebeat_ai
from app.crawlers.reddit_ml import fetch_reddit_ml


def load_all_sources():
    """并行加载所有数据源。"""
    sources = [
        fetch_ai_bot_daily,
        fetch_aibase_news,
        fetch_xix_ai_news,
        fetch_github_trending,
        fetch_openai_blog,
        fetch_huggingface_blog,
        fetch_google_research,
        fetch_techcrunch_ai,
        fetch_venturebeat_ai,
        fetch_reddit_ml,
    ]

    items = []
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        futures = {executor.submit(fn): fn for fn in sources}
        for future in as_completed(futures):
            fn = futures[future]
            try:
                items.extend(future.result())
            except Exception as exc:
                print(f"❌ source error: {fn.__name__} {exc}")
    return items
