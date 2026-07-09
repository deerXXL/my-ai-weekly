import re

import requests
from bs4 import BeautifulSoup

from app.crawlers._http_utils import DEFAULT_HEADERS
from app.models.raw_item import RawItem

URL = "https://research.google/blog/"
BASE = "https://research.google"

SKIP_TITLE_WORDS = (
    "skip",
    "explore",
    "research areas",
    "home",
    "about",
    "careers",
    "contact",
    "subscribe",
    "privacy",
    "terms",
    "专区",
    "research area",
)


def fetch_google_research():
    print("Fetching Google Research blog...")
    items = []
    seen = set()

    try:
        response = requests.get(URL, headers=DEFAULT_HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if "/blog/" not in href or href.rstrip("/") == "/blog":
                continue
            if href.startswith("/"):
                href = BASE + href

            if href in seen:
                continue

            title = anchor.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            if any(word in title.lower() for word in SKIP_TITLE_WORDS):
                continue

            seen.add(href)
            items.append(
                RawItem(
                    title=title,
                    url=href,
                    description=title,
                    source="Google Research",
                    category="研究",
                )
            )
            if len(items) >= 10:
                break
    except Exception as exc:
        print(f"  Google Research error: {exc}")

    print(f"  Google Research: {len(items)} 条")
    return items
