import feedparser
from datetime import datetime

from app.models.raw_item import RawItem


RSS_URL = "https://huggingface.co/blog/feed.xml"


def fetch_huggingface_blog(limit=5):
    """
    获取 Hugging Face Blog 最新文章
    """

    feed = feedparser.parse(RSS_URL)

    items = []

    for entry in feed.entries[:limit]:
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            published_at = datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d")

        items.append(
            RawItem(
                source="HuggingFace",
                title=entry.title,
                description=getattr(entry, "summary", ""),
                url=entry.link,
                published_at=published_at
            )
        )

    return items