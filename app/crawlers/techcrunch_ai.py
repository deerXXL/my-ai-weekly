import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


URL = (
"https://techcrunch.com/category/artificial-intelligence/"
)


def fetch_techcrunch_ai():

    items=[]


    try:

        html=requests.get(
            URL,
            timeout=10
        ).text


        soup=BeautifulSoup(
            html,
            "html.parser"
        )


        for h2 in soup.find_all(
            "h2",
            limit=10
        ):

            title=h2.get_text(
                strip=True
            )


            a=h2.find("a")


            if a:
                published_at = None
                # 尝试从父级文章卡片获取时间
                article = h2.find_parent("article")
                if article:
                    time_tag = article.find("time")
                    if time_tag and time_tag.get("datetime"):
                        try:
                            dt = datetime.fromisoformat(time_tag.get("datetime").replace("Z", "+00:00"))
                            published_at = dt.strftime("%Y-%m-%d")
                        except (ValueError, AttributeError):
                            pass

                items.append(
                    RawItem(
                        title=title,
                        url=a["href"],
                        source="TechCrunch",
                        category="行业资讯",
                        published_at=published_at
                    )
                )


    except Exception as e:

        print(
            "TechCrunch error:",
            e
        )


    return items