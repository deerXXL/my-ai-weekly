import requests
from bs4 import BeautifulSoup

from app.models.raw_item import RawItem


URL = "https://venturebeat.com/category/ai/"


def fetch_venturebeat_ai():

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
            limit=10
        ):

            title=h2.get_text(
                strip=True
            )


            a=h2.find("a")


            if a:

                items.append(

                    RawItem(
                        source="VentureBeat",
                        title=title,
                        description=title,
                        url=a.get("href"),
                        category="行业资讯"
                    )

                )


    except Exception as e:

        print(
            "VentureBeat error:",
            e
        )


    return items