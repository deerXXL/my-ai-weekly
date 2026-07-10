import requests
from bs4 import BeautifulSoup
from datetime import datetime

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

        response = requests.get(
            URL,
            headers=DEFAULT_HEADERS,
            timeout=15
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )


        for anchor in soup.find_all("a", href=True):

            href = anchor["href"].strip()

            title = anchor.get_text(strip=True)


            # 标题为空
            if not title:
                continue


            # 标题太短
            if len(title) < 10:
                continue


            # 导航词过滤
            if any(
                word in title.lower()
                for word in SKIP_TITLE_WORDS
            ):
                continue


            # 只保留文章链接
            if "/blog/" not in href:
                continue


            # 拼接绝对地址
            if href.startswith("/"):
                href = BASE + href


            # 去重
            if href in seen:
                continue


            published_at = None


            # 尝试获取发布时间
            parent = anchor.find_parent()

            if parent:

                time_tag = parent.find("time")

                if time_tag and time_tag.get("datetime"):

                    try:

                        dt = datetime.fromisoformat(
                            time_tag.get("datetime")
                            .replace("Z", "+00:00")
                        )

                        published_at = dt.strftime(
                            "%Y-%m-%d"
                        )

                    except (
                        ValueError,
                        AttributeError
                    ):
                        pass


            seen.add(href)


            items.append(
                RawItem(
                    title=title,
                    url=href,
                    description=title,
                    source="Google Research",
                    category="研究",
                    published_at=published_at
                )
            )


            if len(items) >= 10:
                break


    except Exception as exc:

        print(
            f"  Google Research error: {exc}"
        )


    print(
        f"  Google Research: {len(items)} 条"
    )

    return items