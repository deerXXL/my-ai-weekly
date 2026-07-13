"""阶段二：对筛选后的重点条目补充文章页详情（描述、封面图）。"""
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup

from app.crawlers._http_utils import get_http_session
from app.models.raw_item import RawItem
from app.services.image_enricher import fetch_og_image
from app.services.sources_config import source_enrich_flags

META_DESC = ("og:description", "description", "twitter:description")
MIN_DESC_LEN = 80


def _needs_enrich(item: RawItem) -> bool:
    extra = item.extra or {}
    if extra.get("enriched"):
        return False
    if not source_enrich_flags().get(item.source, True):
        return False
    short_desc = len((item.description or "").strip()) < MIN_DESC_LEN
    missing_image = not extra.get("image_url")
    return short_desc or missing_image


def _extract_description(soup: BeautifulSoup) -> str:
    for prop in META_DESC:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            text = tag["content"].strip()
            if len(text) >= 20:
                return text[:800]
    article = soup.find("article")
    if article:
        ps = article.find_all("p")
        chunks = [p.get_text(strip=True) for p in ps[:3] if p.get_text(strip=True)]
        if chunks:
            return " ".join(chunks)[:800]
    return ""


def enrich_item(item: RawItem) -> RawItem:
    if not _needs_enrich(item):
        return item

    extra = dict(item.extra or {})
    description = item.description or ""
    image_url = extra.get("image_url") or ""

    if not image_url:
        image_url = fetch_og_image(item.url)

    try:
        response = get_http_session().get(item.url, timeout=(5, 12))
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        if len(description) < MIN_DESC_LEN:
            page_desc = _extract_description(soup)
            if page_desc:
                description = page_desc
        if not image_url:
            for prop in ("og:image", "og:image:url", "twitter:image"):
                tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
                if tag and tag.get("content"):
                    image_url = tag["content"].strip()
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url
                    break
    except Exception as exc:
        print(f"  [detail] {item.source} {item.title[:30]}... — {exc}")

    if image_url:
        extra["image_url"] = image_url
    extra["enriched"] = True

    return RawItem(
        source=item.source,
        title=item.title,
        description=description or item.title,
        url=item.url,
        category=item.category,
        author=item.author,
        published_at=item.published_at,
        tags=item.tags,
        extra=extra,
    )


def enrich_items(items: list[RawItem], workers: int = 6) -> list[RawItem]:
    """并行补充详情，保持原顺序。"""
    if not items:
        return items

    to_enrich = [(i, item) for i, item in enumerate(items) if _needs_enrich(item)]
    if not to_enrich:
        print("  [detail] 无需补充详情")
        return items

    print(f"  [detail] 补充 {len(to_enrich)}/{len(items)} 条详情...")
    results = list(items)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(enrich_item, item): idx
            for idx, item in to_enrich
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                print(f"  [detail] 失败 idx={idx} — {exc}")
    return results
