import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


URL = "https://www.jiqizhixin.com/"


def fetch_jiqizhixin():

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


        for a in soup.find_all(
            "a",
            limit=80   # 双周报告需要覆盖14天内容
        ):

            title=a.get_text(
                strip=True
            )


            href=a.get(
                "href"
            )


            if (
                title
                and href
                and len(title)>10
            ):

                if href.startswith("/"):

                    href = (
                        "https://www.jiqizhixin.com"
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
                        source="机器之心",
                        title=title,
                        description=title,
                        url=href,
                        category="行业资讯",
                        published_at=published_at
                    )

                )


    except Exception as e:

        print(
            "机器之心 error:",
            e
        )


    return items[:10]