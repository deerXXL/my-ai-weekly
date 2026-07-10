import re

import requests
from bs4 import BeautifulSoup

from app.crawlers._http_utils import DEFAULT_HEADERS
from app.models.raw_item import RawItem

URL = "https://www.aibase.com/zh/news"
BASE = "https://www.aibase.com"
SOURCE = "AIbase"
LIMIT = 30


def fetch_aibase_news() -> list[RawItem]:
    """抓取 AIbase 中文 AI 资讯。"""
    print(f"Fetching {SOURCE} news...")
    items: list[RawItem] = []
    try:
        response = requests.get(URL, headers=DEFAULT_HEADERS, timeout=30)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        for h3 in soup.find_all("h3"):
            title = h3.get_text(strip=True)
            if len(title) < 8:
                continue

            anchor = h3.find_parent("a", href=True)
            if not anchor:
                continue

            href = anchor["href"].strip()
            if not href.startswith("/news/"):
                continue
            url = BASE + href

            full_text = re.sub(r"^刚刚\.?AIbase", "", anchor.get_text(strip=True))
            description = full_text.replace(title, "", 1).strip() or title

            image_url = ""
            img = anchor.find("img")
            if img and img.get("src"):
                image_url = img["src"]
                if image_url.startswith("//"):
                    image_url = "https:" + image_url

            extra = {"image_url": image_url} if image_url else {}

            items.append(
                RawItem(
                    source=SOURCE,
                    title=title,
                    description=description[:500],
                    url=url,
                    category="行业资讯",
                    extra=extra,
                )
            )
            if len(items) >= LIMIT:
                break
    except Exception as exc:
        print(f"  {SOURCE} error: {exc}")

    print(f"  {SOURCE}: {len(items)} 条")
    return items
