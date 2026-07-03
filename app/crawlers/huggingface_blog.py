import feedparser

from app.models.raw_item import RawItem


RSS_URL = "https://huggingface.co/blog/feed.xml"


def fetch_huggingface_blog(limit=5):
    """
    获取 Hugging Face Blog 最新文章
    """

    feed = feedparser.parse(RSS_URL)

    items = []

    for entry in feed.entries[:limit]:

        items.append(
            RawItem(
                source="HuggingFace",
                title=entry.title,
                description=getattr(entry, "summary", ""),
                url=entry.link
            )
        )

    return items