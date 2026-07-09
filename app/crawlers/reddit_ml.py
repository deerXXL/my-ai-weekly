import requests
from datetime import datetime

from app.models.raw_item import RawItem


URL = (
    "https://www.reddit.com/"
    "r/MachineLearning/top.json"
    "?limit=20&t=week"
)


def fetch_reddit_ml():

    items=[]


    try:

        response=requests.get(
            URL,
            headers={
                "User-Agent":
                "AIReportBot/1.0"
            },
            timeout=10
        )


        data=response.json()


        posts=data["data"]["children"]


        for post in posts:


            info=post["data"]


            title=info.get(
                "title"
            )


            url=(
                "https://reddit.com"
                +
                info.get(
                    "permalink",
                    ""
                )
            )


            created_utc = info.get("created_utc")
            published_at = None
            if created_utc:
                published_at = datetime.fromtimestamp(created_utc).strftime("%Y-%m-%d")


            if not title:
                continue



            items.append(

                RawItem(

                    source="Reddit",

                    title=title,

                    description=(
                        info.get(
                            "selftext",
                            ""
                        )[:200]
                    ),

                    url=url,

                    category="社区讨论",

                    published_at=published_at

                )

            )


    except Exception as e:

        print(
            "Reddit error:",
            e
        )


    return items[:10]