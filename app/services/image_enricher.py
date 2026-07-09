"""从文章页提取 og:image / twitter:image。"""
import requests
from bs4 import BeautifulSoup

from app.crawlers._http_utils import DEFAULT_HEADERS

META_PROPERTIES = (
    "og:image",
    "og:image:url",
    "twitter:image",
    "twitter:image:src",
)


def fetch_og_image(url: str, timeout: int = 12) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        for prop in META_PROPERTIES:
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                image_url = tag["content"].strip()
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                if image_url.startswith("http"):
                    return image_url
    except Exception as exc:
        print(f"  [image] 抓取失败 {url[:50]}... — {exc}")
    return ""
