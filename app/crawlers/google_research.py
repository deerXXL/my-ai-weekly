import requests
from bs4 import BeautifulSoup

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
            limit=30   # 这里建议改大一点
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


            items.append(

                RawItem(
                    title=title,
                    url=href,
                    description=title,
                    source="Google Research",
                    category="研究"
                )

            )


    except Exception as e:

        print(
            "Google Research error:",
            e
        )


    return items[:10]