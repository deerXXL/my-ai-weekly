import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


URL = "https://www.anthropic.com/news"


def fetch_anthropic_blog(limit=40):
    """
    抓取 Anthropic 官方博客
    """

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(URL, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    items = []

    # Anthropic 页面结构相对稳定
    links = soup.find_all("a")

    for a in links:
        href = a.get("href")
        title = a.get_text(strip=True)

        if not href or not title:
            continue

        # 过滤无效内容
        if "/news" not in href:
            continue

        if href.startswith("/"):
            href = "https://www.anthropic.com" + href

        published_at = None
        # 尝试从相邻元素获取日期
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
                source="Anthropic",
                title=title,
                description=title,
                url=href,
                published_at=published_at
            )
        )

        if len(items) >= limit:
            break

    return items