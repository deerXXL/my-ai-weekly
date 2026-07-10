import re

import requests
from bs4 import BeautifulSoup

from app.crawlers._http_utils import DEFAULT_HEADERS
from app.models.raw_item import RawItem

URL = "https://ai-bot.cn/daily-ai-news/"
SOURCE = "AI工具集"
LIMIT = 30


def fetch_ai_bot_daily() -> list[RawItem]:
    """抓取 AI工具集 每日 AI 快讯。"""
    print(f"Fetching {SOURCE} daily news...")
    items: list[RawItem] = []
    try:
        response = requests.get(URL, headers=DEFAULT_HEADERS, timeout=30)
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        for h2 in soup.find_all("h2"):
            link_tag = h2.find("a", href=True)
            if not link_tag:
                continue
            href = link_tag["href"].strip()
            if href.startswith("#") or "/daily-ai-news" in href:
                continue

            title = h2.get_text(strip=True)
            if len(title) < 10:
                continue

            description = ""
            for sibling in h2.next_siblings:
                if getattr(sibling, "name", None) == "h2":
                    break
                if getattr(sibling, "name", None) == "p":
                    description = sibling.get_text(strip=True)
                    break

            items.append(
                RawItem(
                    source=SOURCE,
                    title=title,
                    description=description or title,
                    url=href,
                    category="每日快讯",
                )
            )
            if len(items) >= LIMIT:
                break
    except Exception as exc:
        print(f"  {SOURCE} error: {exc}")

    print(f"  {SOURCE}: {len(items)} 条")
    return items
