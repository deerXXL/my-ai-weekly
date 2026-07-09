import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


RSS_URL = "https://36kr.com/feed-article"


def fetch_36kr_ai():

    items = []

    try:

        response = requests.get(
            RSS_URL,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )


        soup = BeautifulSoup(
            response.text,
            "xml"
        )


        for item in soup.find_all(
            "item",
            limit=50   # 双周报告需要覆盖14天内容
        ):

            title = item.title.text.strip()

            link = item.link.text.strip()

            pub_date = None
            pub_date_tag = item.find("pubDate")
            if pub_date_tag and pub_date_tag.text:
                try:
                    dt = datetime.strptime(pub_date_tag.text.strip(), "%a, %d %b %Y %H:%M:%S %z")
                    pub_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass


            if not title:
                continue


            # AI关键词过滤

            keywords = [
                "AI",
                "人工智能",
                "大模型",
                "模型",
                "机器人",
                "智能体",
                "OpenAI",
                "GPT",
                "Claude"
            ]


            if not any(
                k.lower() in title.lower()
                for k in keywords
            ):
                continue


            items.append(

                RawItem(

                    source="36氪",

                    title=title,

                    description=title,

                    url=link,

                    category="行业资讯",

                    published_at=pub_date

                )

            )


    except Exception as e:

        print(
            "36Kr error:",
            e
        )


    return items[:10]