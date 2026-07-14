"""调用火山方舟 Seedream API 生成周刊封面图。"""
from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from app.crawlers._http_utils import get_http_session
from app.models.daily_report import WeeklyNewsletter
from app.services.llm_signal import load_prompt_template
from config import ARK_API_KEY, ARK_IMAGE_BASE_URL, ARK_IMAGE_MODEL

COVER_FILENAME = "cover.png"
COVER_REL_PATH = f"images/{COVER_FILENAME}"

_image_client: OpenAI | None = None


def _get_image_client() -> OpenAI:
    global _image_client
    if _image_client is None:
        # 运行时校验：防止 ARK_IMAGE_BASE_URL 异常时打到 OpenAI 官方端点
        if not ARK_IMAGE_BASE_URL or not ARK_IMAGE_BASE_URL.startswith("https://ark"):
            raise RuntimeError(
                f"ARK_IMAGE_BASE_URL 异常：{ARK_IMAGE_BASE_URL!r}。"
                "必须以 https://ark 开头（火山方舟端点）。"
            )
        _image_client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_IMAGE_BASE_URL)
    return _image_client


def _news_items_text(newsletter: WeeklyNewsletter) -> str:
    lines = []
    for i, item in enumerate(newsletter.industry_news[:4], start=1):
        lines.append(f"{i}. {item.title}")
    return "\n".join(lines) if lines else "（暂无）"


def _trends_text(newsletter: WeeklyNewsletter) -> str:
    if not newsletter.tech_summary or not newsletter.tech_summary.trends:
        return "（暂无）"
    lines = []
    for trend in newsletter.tech_summary.trends[:3]:
        lines.append(f"{trend.index}. {trend.title}：{trend.body[:60]}")
    return "\n".join(lines)


def _build_image_prompt(newsletter: WeeklyNewsletter) -> str:
    from app.services.llm_signal import call_llm

    ov = newsletter.overview
    template = load_prompt_template("cover_image.md")
    prompt = (
        template.replace("{{brand_name}}", newsletter.brand_name)
        .replace("{{date_range}}", f"{ov.date_start} - {ov.date_end}")
        .replace("{{core_summary}}", ov.core_summary.strip())
        .replace("{{news_items}}", _news_items_text(newsletter))
        .replace("{{trends}}", _trends_text(newsletter))
    )
    result = call_llm(
        prompt,
        system="你是专业 AI 视觉提示词工程师。只输出可直接用于文生图的提示词正文，不要任何前缀后缀。",
        max_tokens=1200,
    )
    return result.strip().strip('"').strip("'")


def _generate_image_url(prompt: str) -> str:
    client = _get_image_client()
    response = client.images.generate(
        model=ARK_IMAGE_MODEL,
        prompt=prompt,
        size="2560x1440",
        extra_body={
            "watermark": False,
            "response_format": "url",
            "sequential_image_generation": "disabled",
        },
    )
    if not response.data:
        raise RuntimeError("Seedream 未返回图片")
    item = response.data[0]
    url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
    if not url:
        raise RuntimeError("Seedream 响应缺少 url")
    return url


def _download_to(dest: Path, url: str) -> None:
    response = get_http_session().get(url, timeout=(10, 120))
    response.raise_for_status()
    dest.write_bytes(response.content)


def generate_cover(newsletter: WeeklyNewsletter, issue_dir: Path) -> str:
    """
    通过 Seedream API 生成封面并保存到 {issue_dir}/images/cover.png。
    返回相对路径 images/cover.png；失败时返回空字符串。
    """
    issue_dir = Path(issue_dir)
    dest = issue_dir / "images" / COVER_FILENAME
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        print("  [cover] 生成提示词...")
        prompt = _build_image_prompt(newsletter)
        print(f"  [cover] 调用 Seedream ({ARK_IMAGE_MODEL})...")
        image_url = _generate_image_url(prompt)
        _download_to(dest, image_url)
        kb = dest.stat().st_size // 1024
        print(f"  [cover] {issue_dir.name}/{COVER_REL_PATH} ({kb}KB)")
        return COVER_REL_PATH
    except Exception as exc:
        print(f"  [cover] 生成失败 — {exc}")
        return ""
