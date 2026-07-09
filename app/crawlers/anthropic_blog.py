import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from app.models.raw_item import RawItem


URL = "https://www.anthropic.com/news"


def _parse_date(text):
    """把 Anthropic 页面里的 'Jun 23, 2026' 转成 yyyy-mm-dd"""
    text = (text or "").strip()
    if not text:
        return None
    # 去掉 time 标签里可能带的前导换行或多余空格
    text = re.sub(r"\s+", " ", text)
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def fetch_anthropic_blog(limit=40):
    """
    抓取 Anthropic 官方新闻/博客列表页。
    页面结构：每个卡片是一个 <a>，内部包含 category、<time>、标题(h4/h3)、摘要(p)。
    """

    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(URL, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    items = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not href:
            continue

        # 只保留新闻/特性页面
        if "/news/" not in href and "/features/" not in href:
            continue

        if href.startswith("/"):
            href = "https://www.anthropic.com" + href

        if href in seen:
            continue
        seen.add(href)

        # 标题：优先取 h2/h3/h4 里的文字
        title_tag = a.find(["h2", "h3", "h4"])
        title = title_tag.get_text(strip=True) if title_tag else ""

        # 摘要：优先取第一个 <p>
        desc_tag = a.find("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 如果选不到标题（防护），再从 <a> 文本里按常见格式拆分
        if not title:
            full_text = a.get_text(" ", strip=True)
            # 尝试匹配：category date title description
            m = re.search(
                r"(?:Product|Announcements|Case Study|Features)?\s*"
                r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\s*"
                r"(.+)",
                full_text,
            )
            if m:
                title = m.group(2).strip()
            else:
                title = full_text

        # 分类
        category = ""
        cat_tag = a.find("span", class_="caption")
        if cat_tag:
            category = cat_tag.get_text(strip=True)

        # 发布日期：优先 <time> 的 datetime，其次文本
        published_at = None
        time_tag = a.find("time")
        if time_tag:
            published_at = _parse_date(time_tag.get("datetime")) or _parse_date(time_tag.get_text())

        # 兜底：从文本里找日期
        if not published_at:
            published_at = _parse_date(a.get_text(" ", strip=True))

        # 没摘要时，标题不要重复
        if not description and title:
            description = title

        items.append(
            RawItem(
                source="Anthropic",
                title=title,
                description=description,
                url=href,
                category=category,
                published_at=published_at,
            )
        )

        if len(items) >= limit:
            break

    return items
