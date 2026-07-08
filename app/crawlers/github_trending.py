import requests
import urllib3

from bs4 import BeautifulSoup
from app.models.raw_item import RawItem


urllib3.disable_warnings()


def fetch_github_trending():
    print("Fetching GitHub Trending...")

    url = "https://github.com/trending?since=weekly"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=60,
        )
        print("GitHub status code:", response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")
        items = []
        articles = soup.find_all("article", class_="Box-row")

        print("GitHub articles found:", len(articles))

        for article in articles[:5]:
            h2 = article.find("h2")
            if not h2:
                continue

            a = h2.find("a")
            if not a:
                continue

            title = a.get_text().strip().replace("\n", "").replace(" ", "")
            link = "https://github.com" + a.get("href")

            desc_tag = article.find("p")
            description = desc_tag.get_text().strip() if desc_tag else "No description"

            items.append(
                RawItem(
                    source="github",
                    title=title,
                    description=description,
                    url=link,
                )
            )

        print("GitHub items:", len(items))
        return items

    except Exception as exc:
        print("GitHub fetch failed:", repr(exc))
        return [
            RawItem(
                source="github",
                title="GitHub trending fetch failed",
                description="GitHub is temporarily unavailable.",
                url="https://github.com",
            )
        ]
