from concurrent.futures import ThreadPoolExecutor, as_completed

from app.crawlers.ai_bot_daily import fetch_ai_bot_daily
from app.crawlers.aibase_news import fetch_aibase_news
from app.crawlers.xix_ai_news import fetch_xix_ai_news
from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.openai_blog import fetch_openai_blog
from app.crawlers.anthropic_blog import fetch_anthropic_blog
from app.crawlers.huggingface_blog import fetch_huggingface_blog
from app.crawlers.google_research import fetch_google_research
from app.crawlers.techcrunch_ai import fetch_techcrunch_ai
from app.crawlers.venturebeat_ai import fetch_venturebeat_ai
from app.crawlers.reddit_ml import fetch_reddit_ml
from app.crawlers.jiqizhixin_ai import fetch_jiqizhixin as fetch_jiqizhixin_ai
from app.crawlers.kr36_ai import fetch_36kr_ai as fetch_kr36_ai

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
        (fetch_jiqizhixin_ai, {}),
        (fetch_kr36_ai, {}),
        (fetch_reddit_ml, {}),
    ]

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:


        futures = {
            executor.submit(source, **kwargs): source
            for source, kwargs in sources
        }


        for future in as_completed(futures):

            source = futures[future]

            try:

                result = future.result()

                items.extend(result)

                print(
                    f"✅ {source.__name__}: {len(result)} 条"
                )


            except Exception as e:

                print(
                    f"❌ source error: {source.__name__}",
                    e
                )


    return items