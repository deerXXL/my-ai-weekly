import requests
from bs4 import BeautifulSoup
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

        items.append(
            RawItem(
                source="OpenAI",
                title=title,
                description=title,
                url=href
            )
        )

        if len(items) >= limit:
            break

    return items