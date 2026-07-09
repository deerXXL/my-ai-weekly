import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app.models.raw_item import RawItem


def fetch_openai_blog(limit=5):
    url = "https://openai.com/news/"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    items = []

    for a in soup.find_all("a"):
        title = a.get_text(strip=True)
        href = a.get("href")

        if not title or not href:
            continue

        if href.startswith("/"):
            href = "https://openai.com" + href

        if "/news" not in href:
            continue

        # 尝试从相邻元素获取日期
        published_at = None
        parent = a.find_parent()
        if parent:
            time_tag = parent.find("time")
            if time_tag and time_tag.get("datetime"):
                try:
                    dt = datetime.fromisoformat(time_tag.get("datetime").replace("Z", "+00:00"))
                    published_at = dt.strftime("%Y-%m-%d")
                except (ValueError, AttributeError):
                    pass

        items.append(
            RawItem(
                source="OpenAI",
                title=title,
                description=title,
                url=href,
                published_at=published_at
            )
        )

        if len(items) >= limit:
            break

    return items