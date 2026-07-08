import requests
from bs4 import BeautifulSoup

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

                items.append(
                    RawItem(
                        title=title,
                        url=a["href"],
                        source="TechCrunch",
                        category="行业资讯"
                    )
                )


    except Exception as e:

        print(
            "TechCrunch error:",
            e
        )


    return items