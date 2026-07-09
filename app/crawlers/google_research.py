import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


URL = "https://research.google/blog/"


# Google Research 页面过滤关键词
IGNORE_WORDS = [

    "Skip",
    "Explore",
    "Research areas",
    "Areas",
    "Home",
    "About",
    "Careers",
    "Contact",
    "Subscribe",
    "Privacy",
    "Terms"

]


def fetch_google_research():

    items=[]

    try:

        html = requests.get(
            URL,
            timeout=10
        ).text


        soup = BeautifulSoup(
            html,
            "html.parser"
        )


        for a in soup.find_all(
            "a",
            limit=80   # 双周报告需要覆盖14天内容
        ):

            title = a.get_text(strip=True)


            if not title:
                continue


            # 去除导航内容
            if any(
                word.lower() in title.lower()
                for word in IGNORE_WORDS
            ):
                continue


            # 太短的一般不是文章
            if len(title) < 15:
                continue


            href = a.get("href")


            if not href:
                continue


            if href.startswith("/"):

                href = (
                    "https://research.google"
                    + href
                )

            published_at = None
            # 尝试从父级获取时间标签
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
                    title=title,
                    url=href,
                    description=title,
                    source="Google Research",
                    category="研究",
                    published_at=published_at
                )

            )


    except Exception as e:

        print(
            "Google Research error:",
            e
        )


    return items[:10]