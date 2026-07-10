"""闪联AI周刊 Markdown / HTML 渲染与导出。"""
from collections import OrderedDict
from html import escape
import json
import re
from pathlib import Path

from app.models.daily_report import WeeklyNewsletter
from app.services.issue_paths import find_latest_newsletter_json, issue_name, OUTPUT_DIR
from config import NewsletterConfig, load_newsletter_config

_REPORT_OUTPUT_DIR = OUTPUT_DIR


def _find_any_latest_report_path() -> Path | None:
    """查找最新报告 JSON，兼容新旧两种目录结构。

    优先级：
    1. output/latest.json（旧格式）
    2. output/weekly-YYYY-MM-DD/newsletter.json（新格式）
    3. output/weekly-YYYY-MM-DD.json（旧格式，无子目录）
    """
    # 1) 旧版 latest.json
    latest = _REPORT_OUTPUT_DIR / "latest.json"
    if latest.exists():
        return latest

    # 2) 新版 weekly-日期/newsletter.json
    nl = find_latest_newsletter_json()
    if nl and nl.exists():
        return nl

    # 3) 旧版 weekly-日期.json（平铺在 output/ 下）
    candidates = sorted(
        _REPORT_OUTPUT_DIR.glob("weekly-*.json"),
        key=lambda p: p.stem,
        reverse=True,
    )
    if candidates:
        return candidates[0]

    return None


def load_latest_report_dict() -> dict | None:
    """加载最新报告的原始字典，兼容新旧格式。"""
    target = _find_any_latest_report_path()
    if target is None or not target.exists():
        return None
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 如果是旧格式（有 signals 但没有 brand_name），补充缺失的元信息
    # 使 /api/report 和 /api/meta 都能正确返回数据
    if "signals" in data and "brand_name" not in data:
        date_str = data.get("date", "")
        data.setdefault("brand_name", "闪联AI周刊")
        data.setdefault("title", data.get("title") or "AI双周产品周报")
        if not data.get("period_start") or not data.get("period_end"):
            from datetime import datetime, timedelta
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d")
                data.setdefault("period_start", (d - timedelta(days=14)).strftime("%Y-%m-%d"))
                data.setdefault("period_end", date_str)
            except (ValueError, TypeError):
                pass

    return data


def _issue_slug(newsletter: WeeklyNewsletter) -> str:
    date_tag = newsletter.date or (newsletter.generated_at[:10] if newsletter.generated_at else "")
    return issue_name(date_tag)


LIST_INDENT = "    "


def validate_markdown_structure(md: str) -> list[str]:
    """校验 Markdown 结构，返回问题列表（空=通过）。"""
    issues: list[str] = []
    if "## 🧪 实测体验" in md:
        issues.append("不应包含独立实测体验栏目")
    if re.search(r"^>\s*\*\*Prompt", md, re.M):
        issues.append("不应包含实测 Prompt 引用块")

    in_trends = False
    for i, line in enumerate(md.splitlines(), start=1):
        if line.startswith("### ☀️ 核心趋势"):
            in_trends = True
            continue
        if in_trends and line.startswith("### "):
            in_trends = False
        if in_trends and re.match(r"^\d+\.\s+\*\*", line):
            if i >= len(md.splitlines()):
                continue
            next_lines = md.splitlines()[i : i + 3]
            body_lines = [ln for ln in next_lines if ln.strip() and not ln.startswith("#")]
            if body_lines and not body_lines[0].startswith(LIST_INDENT):
                issues.append(f"第{i+1}行：趋势正文缺少列表缩进")

    if "### 🔮 可行性思考" in md:
        chunk = md.split("### 🔮 可行性思考", 1)[1]
        for match in re.finditer(r"^(\d+\.\s+\*\*.+\*\*)\n\n(- )", chunk, re.M):
            issues.append(f"可行性条目 '{match.group(1)[:20]}' 的子列表缺少缩进")

    return issues


def _render_overview(newsletter: WeeklyNewsletter, cfg: NewsletterConfig) -> list[str]:
    ov = newsletter.overview
    return [
        f"# {newsletter.brand_name}",
        "",
        "---",
        "",
        f"## {cfg.overview.icon} {cfg.overview.label}",
        "",
        f"**时间范围：** {ov.date_start} - {ov.date_end}",
        "",
        f"**本期编辑：** {ov.editor}",
        "",
        f"**核心摘要：** {ov.core_summary.strip()}",
        "",
    ]


def _resolve_newsletter(report: dict | WeeklyNewsletter | None) -> WeeklyNewsletter:
    if isinstance(report, WeeklyNewsletter):
        return report
    if isinstance(report, dict):
        return _dict_to_newsletter(report)
    raw = load_latest_report_dict()
    if raw is None:
        raise FileNotFoundError("暂无可导出的周报数据")
    return _dict_to_newsletter(raw)


def _dict_to_newsletter(report: dict) -> WeeklyNewsletter:
    """将 dict 转为 WeeklyNewsletter，兼容新旧两种 JSON 格式。

    - 新格式：含 brand_name / overview / industry_news
    - 旧格式：含 title / summary / signals / items
    """
    # 新格式直接用 from_dict
    if "brand_name" in report and "overview" in report:
        return WeeklyNewsletter.from_dict(report)

    # 旧格式：signals → industry_news，补全 overview 等字段
    from datetime import datetime, timedelta
    from app.models.daily_report import (
        IndustryNewsItem,
        OverviewBlock,
    )

    date_str = report.get("date", "") or (report.get("generated_at") or "")[:10]
    period_start = report.get("period_start", "")
    period_end = report.get("period_end", "")
    if (not period_start or not period_end) and date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            period_start = period_start or (d - timedelta(days=14)).strftime("%Y-%m-%d")
            period_end = period_end or date_str
        except (ValueError, TypeError):
            pass

    industry_news = []
    for s in report.get("signals", []):
        title = s.get("title") or s.get("signal", "")
        industry_news.append(IndustryNewsItem(
            date_label=s.get("published_at") or date_str,
            title=title,
            summary=s.get("insight") or s.get("signal", ""),
            url=s.get("url") or "",
            image_url="",
            usage_note="",
        ))

    return WeeklyNewsletter(
        brand_name=report.get("title") or "闪联AI周刊",
        overview=OverviewBlock(
            date_start=period_start,
            date_end=period_end,
            editor="产品资讯组",
            core_summary=report.get("summary", ""),
        ),
        industry_news=industry_news,
        generated_at=report.get("generated_at", ""),
        issue_number=int(report.get("issue_number", 0) or 0),
        period_start=period_start,
        period_end=period_end,
        total_sources=int(report.get("total_sources", 0) or 0),
    )


def _image_src_for_html(image_url: str, issue_slug: str) -> str:
    """本地图片用 /issues/{issue_slug}/images/... 供 Flask 静态路由。"""
    if not image_url:
        return ""
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    if image_url.startswith("images/"):
        return f"/issues/{issue_slug}/{image_url}"
    return "/" + image_url.lstrip("/")


def _group_industry_by_date(newsletter: WeeklyNewsletter) -> OrderedDict[str, list]:
    grouped: OrderedDict[str, list] = OrderedDict()
    for item in newsletter.industry_news:
        grouped.setdefault(item.date_label, []).append(item)
    return grouped


def _render_industry(newsletter: WeeklyNewsletter, cfg: NewsletterConfig) -> list[str]:
    grouped = _group_industry_by_date(newsletter)
    if not grouped:
        return []
    lines = [f"## {cfg.industry.icon} {cfg.industry.label}", ""]
    for date_label, items in grouped.items():
        lines.extend([f"### {date_label}", ""])
        for item in items:
            if item.image_url:
                lines.extend([f"![{item.title}]({item.image_url})", ""])
            lines.append(f"- **{item.title}**")
            lines.append("")
            lines.append(f"{LIST_INDENT}{item.summary.strip()}")
            if item.usage_note.strip():
                lines.append("")
                lines.append(
                    f"{LIST_INDENT}**使用说明：** {item.usage_note.strip()}"
                )
            lines.append("")
        lines.append("")
    return lines


def _render_tech_summary(newsletter: WeeklyNewsletter, cfg: NewsletterConfig) -> list[str]:
    tech = newsletter.tech_summary
    if tech is None:
        return []
    lines = [
        f"## {cfg.tech_summary_icon} {cfg.tech_summary_label_prefix}：{tech.title_suffix}",
        "",
        "### ☀️ 核心趋势",
        "",
    ]
    for trend in tech.trends:
        lines.extend([
            f"{trend.index}. **{trend.title}**",
            "",
            f"{LIST_INDENT}{trend.body.strip()}",
            "",
        ])
    if tech.feasibility:
        lines.extend(["### 🔮 可行性思考", ""])
        for group in tech.feasibility:
            lines.append(f"{group.index}. **{group.title}**")
            lines.append("")
            for bullet in group.bullets:
                lines.append(f"{LIST_INDENT}- {bullet.strip()}")
            lines.append("")
    return lines


def build_export_markdown(report: dict | WeeklyNewsletter | None = None) -> str:
    newsletter = _resolve_newsletter(report)
    cfg = load_newsletter_config()
    lines: list[str] = []
    lines.extend(_render_overview(newsletter, cfg))
    lines.extend(_render_industry(newsletter, cfg))
    lines.extend(_render_tech_summary(newsletter, cfg))
    return "\n".join(lines).rstrip() + "\n"


def _format_bullet_html(text: str) -> str:
    escaped = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def build_export_html(report: dict | WeeklyNewsletter | None = None) -> str:
    newsletter = _resolve_newsletter(report)
    cfg = load_newsletter_config()
    ov = newsletter.overview
    issue_slug = _issue_slug(newsletter)
    grouped = _group_industry_by_date(newsletter)

    industry_html = []
    for date_label, items in grouped.items():
        industry_html.append(f'<h3 class="date-label">{escape(date_label)}</h3>')
        for item in items:
            img_html = ""
            if item.image_url:
                src = _image_src_for_html(item.image_url, issue_slug)
                img_html = (
                    f'<img class="news-image" src="{escape(src)}" '
                    f'alt="{escape(item.title)}" loading="lazy">'
                )
            usage_html = ""
            if item.usage_note.strip():
                usage_html = (
                    f'<p class="news-usage"><strong>使用说明：</strong>'
                    f"{escape(item.usage_note.strip())}</p>"
                )
            industry_html.append(
                f'<div class="news-item">'
                f"{img_html}"
                f'<p class="news-title">• <strong>{escape(item.title)}</strong></p>'
                f'<p class="news-summary">{escape(item.summary)}</p>'
                f"{usage_html}"
                f"</div>"
            )

    trends_html = []
    tech = newsletter.tech_summary
    if tech:
        for trend in tech.trends:
            trends_html.append(
                f'<div class="trend-item">'
                f"<p class=\"trend-heading\"><strong>{trend.index}. "
                f"{escape(trend.title)}</strong></p>"
                f'<p class="trend-body">{escape(trend.body)}</p>'
                f"</div>"
            )

    feasibility_html = []
    if tech and tech.feasibility:
        for group in tech.feasibility:
            bullets = "".join(
                f"<li>{_format_bullet_html(b)}</li>" for b in group.bullets
            )
            feasibility_html.append(
                f'<div class="trend-item">'
                f"<p class=\"trend-heading\"><strong>{group.index}. "
                f"{escape(group.title)}</strong></p>"
                f"<ul class=\"feasibility-list\">{bullets}</ul>"
                f"</div>"
            )

    tech_block = ""
    if tech:
        tech_block = f"""
<section>
  <h2>{cfg.tech_summary_icon} {cfg.tech_summary_label_prefix}：{escape(tech.title_suffix)}</h2>
  <h3>☀️ 核心趋势</h3>
  {''.join(trends_html)}
  <h3>🔮 可行性思考</h3>
  {''.join(feasibility_html)}
</section>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(newsletter.brand_name)}</title>
<style>
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
    max-width: 720px; margin: 0 auto; padding: 32px 24px;
    color: #222; line-height: 1.7; background: #fff;
  }}
  h1 {{ text-align: center; font-size: 28px; margin-bottom: 8px; }}
  hr {{ border: none; border-top: 1px solid #333; margin: 16px 0 24px; }}
  h2 {{ font-size: 18px; margin-top: 32px; }}
  h3 {{ font-size: 15px; margin-top: 20px; }}
  h3.date-label {{ color: #007bff; font-weight: 600; }}
  .meta p {{ margin: 6px 0; }}
  .news-item {{ margin-bottom: 20px; }}
  .news-image {{ max-width: 100%; border-radius: 8px; margin-bottom: 8px; display: block; }}
  .news-title {{ margin-bottom: 6px; font-weight: 600; }}
  .news-summary {{ margin: 0 0 8px 16px; color: #444; }}
  .news-usage {{ margin: 0 0 0 16px; color: #555; font-size: 14px; }}
  .trend-item {{ margin-bottom: 20px; }}
  .trend-heading {{ margin-bottom: 6px; }}
  .trend-body {{ margin: 0 0 0 16px; color: #444; }}
  .feasibility-list {{ margin: 4px 0 0 16px; padding-left: 20px; }}
  ul {{ padding-left: 20px; }}
  a {{ color: #007bff; }}
</style>
</head>
<body>
  <h1>{escape(newsletter.brand_name)}</h1>
  <hr>
  <section>
    <h2>{cfg.overview.icon} {cfg.overview.label}</h2>
    <div class="meta">
      <p><strong>时间范围：</strong>{escape(ov.date_start)} - {escape(ov.date_end)}</p>
      <p><strong>本期编辑：</strong>{escape(ov.editor)}</p>
      <p><strong>核心摘要：</strong>{escape(ov.core_summary)}</p>
    </div>
  </section>
  <section>
    <h2>{cfg.industry.icon} {cfg.industry.label}</h2>
    {''.join(industry_html)}
  </section>
  {tech_block}
</body>
</html>
"""
