import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


URL = "https://venturebeat.com/category/ai/"


def fetch_venturebeat_ai(limit=50):

    items=[]


    try:

        response=requests.get(
            URL,
            timeout=10,
            headers={
                "User-Agent":"Mozilla/5.0"
            }
        )


        soup=BeautifulSoup(
            response.text,
            "html.parser"
        )


        for h2 in soup.find_all(
            "h2",
            limit=limit
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
                        source="VentureBeat",
                        title=title,
                        description=title,
                        url=a.get("href"),
                        category="行业资讯",
                        published_at=published_at
                    )

                )


    except Exception as e:

        print(
            "VentureBeat error:",
            e
        )


    return items