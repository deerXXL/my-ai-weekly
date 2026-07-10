"""LLM 判断配图与资讯是否匹配，并保存到本地。"""
from app.services.image_enricher import fetch_og_image
from app.services.image_storage import download_image
from app.services.llm_signal import call_llm, load_prompt_template, parse_json_response

MATCH_THRESHOLD = 0.7


def _evaluate_image(title: str, summary: str, image_url: str) -> tuple[bool, float]:
    template = load_prompt_template("match_image.md")
    prompt = (
        template.replace("{{title}}", title)
        .replace("{{summary}}", summary[:300])
        .replace("{{image_url}}", image_url)
    )
    try:
        raw = call_llm(prompt)
        data = parse_json_response(raw)
        score = float(data.get("score") or 0)
        relevant = bool(data.get("relevant")) and score >= MATCH_THRESHOLD
        return relevant, score
    except Exception as exc:
        print(f"  [image-match] LLM 失败 — {exc}")
        return False, 0.0


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
    解析、验证并下载配图，返回相对本期目录的路径（如 images/img-0.jpg）。
    trust_candidate=True 时跳过 LLM 匹配（聚合源已带封面图）。
    """
    remote_url = candidate_image.strip()
    fetched = False
    if not remote_url and page_url:
        remote_url = fetch_og_image(page_url)
        fetched = bool(remote_url)
    if not remote_url:
        return ""

    if trust_candidate and not fetched:
        print(f"  [image-match] ✓ 聚合源封面 {title[:30]}...")
    else:
        relevant, score = _evaluate_image(title, summary, remote_url)
        if not relevant:
            print(f"  [image-match] ✗ score={score:.2f} {title[:30]}...")
            return ""
        print(f"  [image-match] ✓ score={score:.2f} {title[:30]}...")

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
