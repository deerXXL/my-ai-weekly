import requests
from bs4 import BeautifulSoup
from app.models.raw_item import RawItem


def fetch_github_trending():
    print("🚀 开始抓取 GitHub Trending...")

    url = "https://github.com/trending/javascript?since=daily"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        print("状态码:", response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")

        items = []
        articles = soup.find_all("article", class_="Box-row")

        print("抓到 articles:", len(articles))

        for article in articles[:5]:

            h2 = article.find("h2")
            if not h2:
                continue

            a = h2.find("a")
            if not a:
                continue

            title = a.get_text().strip().replace("\n", "").replace(" ", "")
            link = "https://github.com" + a.get("href")

            desc_tag = article.find("p")
            description = desc_tag.get_text().strip() if desc_tag else "暂无描述"

            items.append(
                RawItem(
                    source="github",
                    title=title,
                    description=description,
                    url=link
                )
            )

        print("最终 items 数量:", len(items))
        return items

    except Exception as e:
        print("❌ 抓取失败:", e)
        return []