import json

import requests
from bs4 import BeautifulSoup

from app.crawlers._http_utils import DEFAULT_HEADERS
from app.models.raw_item import RawItem

URL = "https://xix.ai/zh/ainews/ainews"
SOURCE = "XixAI"
LIMIT = 30


def fetch_xix_ai_news() -> list[RawItem]:
    """抓取 XixAI 中文 AI 资讯（JSON-LD ItemList）。"""
    print(f"Fetching {SOURCE} news...")
    items: list[RawItem] = []
    try:
        response = requests.get(URL, headers=DEFAULT_HEADERS, timeout=30)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except json.JSONDecodeError:
                continue
            if not isinstance(data, dict) or data.get("@type") != "ItemList":
                continue

            for element in data.get("itemListElement") or []:
                article = element.get("item") or {}
                title = (article.get("headline") or "").strip()
                description = (article.get("description") or "").strip()
                url = (article.get("url") or article.get("@id") or "").strip()
                if not title or not url:
                    continue

                image_url = ""
                image = article.get("image")
                if isinstance(image, str):
                    image_url = image
                elif isinstance(image, dict):
                    image_url = image.get("url") or ""

                extra = {"image_url": image_url} if image_url else {}
                items.append(
                    RawItem(
                        source=SOURCE,
                        title=title,
                        description=description or title,
                        url=url,
                        category="行业资讯",
                        extra=extra,
                    )
                )
                if len(items) >= LIMIT:
                    break
            if items:
                break
    except Exception as exc:
        print(f"  {SOURCE} error: {exc}")

    print(f"  {SOURCE}: {len(items)} 条")
    return items
