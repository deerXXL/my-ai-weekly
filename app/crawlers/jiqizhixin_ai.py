import requests
from bs4 import BeautifulSoup

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
            limit=30
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


                items.append(

                    RawItem(
                        source="机器之心",
                        title=title,
                        description=title,
                        url=href,
                        category="行业资讯"
                    )

                )


    except Exception as e:

        print(
            "机器之心 error:",
            e
        )


    return items[:10]