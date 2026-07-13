"""解析配图 URL 并下载到本地（不使用 LLM 匹配）。"""
from app.services.image_enricher import fetch_og_image
from app.services.image_storage import download_image


def resolve_image_url(
    title: str,
    summary: str,
    *,
    page_url: str = "",
    candidate_image: str = "",
    date_tag: str = "",
    index: int = 0,
    trust_candidate: bool = False,
) -> str:
    """
    获取配图 URL 并下载。
    优先使用爬虫/详情阶段提供的 candidate_image，否则抓 og:image。
    """
    _ = title, summary, trust_candidate  # 保留签名供 pipeline 调用

    remote_url = candidate_image.strip()
    if not remote_url and page_url:
        remote_url = fetch_og_image(page_url)
    if not remote_url:
        return ""

    if not date_tag:
        return remote_url

    from app.services.issue_paths import ensure_issue_dir

    folder = ensure_issue_dir(date_tag)
    return download_image(
        remote_url,
        folder,
        index,
        referer=page_url or remote_url,
    )
