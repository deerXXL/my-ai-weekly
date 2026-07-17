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


def _report_date_of(path: Path) -> str:
    """从候选路径中提取日期标签 YYYY-MM-DD，用于比较新旧。"""
    name = path.name
    if name == "latest.json":
        # 读取其内部 date 字段
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
            return (d.get("date") or (d.get("generated_at") or "")[:10] or "")[:10]
        except Exception:
            return ""
    # 1) 平铺旧格式：output/weekly-YYYY-MM-DD.json
    if name.startswith("weekly-") and name.endswith(".json"):
        return path.stem.replace("weekly-", "")
    # 2) 新格式目录内：output/weekly-YYYY-MM-DD/newsletter.json —— 取父目录
    if path.parent.name.startswith("weekly-"):
        return path.parent.name.replace("weekly-", "")
    return ""


def _find_any_latest_report_path() -> Path | None:
    """查找最新报告 JSON，兼容新旧两种目录结构。

    按报告日期挑选真正的「最新一期」，而不是盲目优先某个文件名。
    候选：
      - output/latest.json（旧格式，可能陈旧）
      - output/weekly-YYYY-MM-DD/newsletter.json（新格式）
      - output/weekly-YYYY-MM-DD.json（旧格式，平铺）
    """
    candidates: list[Path] = []

    latest = _REPORT_OUTPUT_DIR / "latest.json"
    if latest.exists():
        candidates.append(latest)

    nl = find_latest_newsletter_json()
    if nl and nl.exists():
        candidates.append(nl)

    for p in _REPORT_OUTPUT_DIR.glob("weekly-*.json"):
        if p.exists():
            candidates.append(p)

    if not candidates:
        return None

    # 按提取到的日期降序，取最新的；日期相同则按 mtime 降序
    candidates.sort(
        key=lambda p: (_report_date_of(p), p.stat().st_mtime),
        reverse=True,
    )
    return candidates[0]


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
    lines = [
        f"# {newsletter.brand_name}",
        "",
        "---",
        "",
    ]
    lines.extend([
        f"## {cfg.overview.icon} {cfg.overview.label}",
        "",
        f"**时间范围：** {ov.date_start} - {ov.date_end}",
        "",
        f"**本期编辑：** {ov.editor}",
        "",
        f"**核心摘要：** {ov.core_summary.strip()}",
        "",
    ])
    if ov.cover_image:
        # 去掉可能带上的期号目录前缀，统一为 images/cover.png，
        # 这样在 issue 目录内/导出 ZIP 内都能用相对路径解析到图片
        cover = ov.cover_image
        if cover.startswith("weekly-"):
            cover = "/".join(cover.split("/")[1:])
        lines.extend([f"![{newsletter.brand_name}封面]({cover})", ""])
    return lines


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


def _image_src_for_html(
    image_url: str,
    issue_slug: str,
    relative: bool = False,
) -> str:
    """本地图片地址。

    - relative=False（网页/服务器预览）：用 /issues/{issue_slug}/images/... 供 Flask 静态路由
    - relative=True（导出 ZIP 内离线查看）：统一为相对路径 images/...，脱离服务器也能显示
    """
    if not image_url:
        return ""
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    # 统一成 images/xxx：去掉开头斜杠与可能带上的期号目录前缀
    rel = image_url.lstrip("/")
    if rel.startswith("weekly-"):
        rel = "/".join(rel.split("/")[1:])
    if relative:
        return rel
    if rel.startswith("images/"):
        return f"/issues/{issue_slug}/{rel}"
    return "/" + rel


def _group_industry_by_date(newsletter: WeeklyNewsletter) -> OrderedDict[str, list]:
    grouped: OrderedDict[str, list] = OrderedDict()
    for item in newsletter.industry_news:
        grouped.setdefault(item.date_label, []).append(item)
    return grouped


def _render_hot_topics(newsletter: WeeklyNewsletter, cfg: NewsletterConfig) -> list[str]:
    """从 industry_news 中取前 N 条作为热点资讯（放在行业动态上方）。"""
    count = cfg.hot_topics_count
    top_items = newsletter.industry_news[:count]
    if not top_items:
        return []
    lines = [f"## {cfg.hot_topics.icon} {cfg.hot_topics.label}", ""]
    for i, item in enumerate(top_items, 1):
        lines.append(f"**{i}. {item.title}**")
        lines.append("")
        lines.append(f"{LIST_INDENT}{item.summary.strip()}")
        lines.append("")
    return lines


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
            f"**{trend.title}**",
            "",
            f"{LIST_INDENT}{trend.body.strip()}",
            "",
        ])
    if tech.feasibility:
        lines.extend(["### 🔮 可行性思考", ""])
        for group in tech.feasibility:
            lines.append(f"**{group.title}**")
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
    lines.extend(_render_hot_topics(newsletter, cfg))
    lines.extend(_render_industry(newsletter, cfg))
    lines.extend(_render_tech_summary(newsletter, cfg))
    return "\n".join(lines).rstrip() + "\n"


def _format_bullet_html(text: str) -> str:
    escaped = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _render_feasibility_bullet(text: str) -> str:
    """将 '**标签：** 描述' 解析为「彩色标签 + 描述」的列表项；无标签则纯文本。

    支持两种写法：
      - '**政府场景：** 阿尔伯塔省...'  → 标签 chip + 描述
      - '**政府场景** 阿尔伯塔省...'    → 同上（无冒号）
      - '需同步配套...'                → 纯文本条目
    """
    s = text.strip()
    m = re.match(r"^\*\*(.+?)\*\*\s*[:：]\s*(.*)$", s)
    if not m:
        m = re.match(r"^\*\*(.+?)\*\*\s+(.*)$", s)
    if m:
        label = m.group(1).strip()
        desc = m.group(2).strip()
        return (
            f'<li class="feas-item">'
            f'<span class="feas-tag">{escape(label)}</span>'
            f'<span class="feas-desc">{escape(desc)}</span>'
            f"</li>"
        )
    return f'<li class="feas-item feas-plain">{escape(s)}</li>'


def build_export_html(
    report: dict | WeeklyNewsletter | None = None,
    relative: bool = False,
) -> str:
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
                src = _image_src_for_html(item.image_url, issue_slug, relative)
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
                f"<p class=\"trend-heading\"><strong>{escape(trend.title)}</strong></p>"
                f'<p class="trend-body">{escape(trend.body)}</p>'
                f"</div>"
            )

    feasibility_html = []
    if tech and tech.feasibility:
        for idx, group in enumerate(tech.feasibility, 1):
            bullets_html = "".join(
                _render_feasibility_bullet(b) for b in group.bullets
            )
            summary_html = ""
            if group.summary.strip():
                summary_html = (
                    f'<p class="feas-summary">{escape(group.summary.strip())}</p>'
                )
            feasibility_html.append(
                f'<div class="feas-card">'
                f'<div class="feas-header">'
                f'<span class="feas-badge">{idx}</span>'
                f'<span class="feas-title">{escape(group.title)}</span>'
                f"</div>"
                f"{summary_html}"
                f'<ul class="feas-list">{bullets_html}</ul>'
                f"</div>"
            )

    # ---- 热点资讯（行业动态上方）----
    hot_items = newsletter.industry_news[:cfg.hot_topics_count]
    hot_html = []
    if hot_items:
        for i, item in enumerate(hot_items, 1):
            hot_html.append(
                f'<div class="hot-item">'
                f'<span class="hot-rank">{i}</span>'
                f'<div class="hot-content">'
                f'<p class="hot-title"><strong>{escape(item.title)}</strong></p>'
                f'<p class="hot-summary">{escape(item.summary)}</p>'
                f'</div></div>'
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

    cover_html = ""
    if ov.cover_image:
        src = _image_src_for_html(ov.cover_image, issue_slug, relative)
        cover_html = (
            f'<img class="cover-image" src="{escape(src)}" '
            f'alt="{escape(newsletter.brand_name)}封面">'
        )

    # 邮件安全布局：外层 100% 宽 table 居中 + 内层固定宽 table
    # 兼容 Outlook（Word 引擎）/ Gmail / Apple Mail 等主流邮件客户端
    hot_section = ""
    if hot_html:
        hot_section = f"""
<section>
  <h2>{cfg.hot_topics.icon} {cfg.hot_topics.label}</h2>
  <div class="hot-list">
    {''.join(hot_html)}
  </div>
</section>
"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(newsletter.brand_name)}</title>
<!--[if mso]>
<style type="text/css">
  body,table,td{{font-family:Arial,sans-serif !important;}}
</style>
<![endif]-->
<style>
  body {{margin:0;padding:0;background-color:#f4f4f4;}}
  .wrapper-table {{width:100%;background-color:#f4f4f4;}}
  .content-table {{width:720px;max-width:92%;margin:0 auto;background-color:#fff;
                   border-radius:8px;}}
  .inner-padding {{padding:32px 28px;}}
  body {{font-family:"PingFang SC","Microsoft YaHei","Helvetica Neue",Helvetica,Arial,sans-serif;
            color:#222;line-height:1.7;font-size:15px;-webkit-font-smoothing:antialiased;}}
  h1 {{text-align:center;font-size:26px;margin-bottom:6px;color:#111;}}
  hr {{border:none;border-top:1.5px solid #333;margin:16px auto 24px;width:100%;}}
  .cover-image {{width:100%;border-radius:10px;margin:16px 0 22px;display:block;}}
  h2 {{font-size:17px;margin-top:28px;color:#111;border-left:4px solid #a62c2c;padding-left:10px;}}
  h3 {{font-size:15px;margin-top:18px;color:#333;}}
  h3.date-label {{color:#d95030;font-weight:600;font-size:14px;}}
  .meta p {{margin:6px 0;font-size:14px;color:#444;}}
  /* 热点资讯 */
  .hot-list {{margin:12px 0 8px;}}
  .hot-item {{display:flex;gap:12px;margin-bottom:14px;padding:10px 12px;
               background:#fff8f0;border-left:3px solid #e6a23c;border-radius:6px;}}
  .hot-rank {{flex-shrink:0;width:24px;height:24px;line-height:24px;text-align:center;
              background:#e6a23c;color:#fff;border-radius:50%;font-size:13px;font-weight:bold;}}
  .hot-content {{flex:1;min-width:0;}}
  .hot-title {{margin:0 0 4px;font-size:14px;font-weight:600;}}
  .hot-summary {{margin:0;color:#555;font-size:13px;line-height:1.6;}}
  /* 行业动态 */
  .news-item {{margin-bottom:18px;padding-bottom:14px;border-bottom:1px dashed #e0e0e0;}}
  .news-item:last-child {{border-bottom:none;}}
  .news-image {{max-width:100%;border-radius:8px;margin-bottom:8px;display:block;}}
  .news-title {{margin-bottom:5px;font-weight:600;font-size:14.5px;}}
  .news-summary {{margin:0 0 6px 16px;color:#444;font-size:14px;}}
  .news-usage {{margin:0 0 0 16px;color:#666;font-size:13px;
                 background:#f9f9f9;padding:6px 10px;border-radius:4px;display:inline-block;}}
  /* 技术总结 - 核心趋势 */
  .trend-item {{margin-bottom:16px;padding:12px 14px;background:#f8fafc;border-radius:6px;border-left:3px solid #365772;}}
  .trend-heading {{margin-bottom:5px;font-size:14.5px;color:#1a3c5e;}}
  .trend-body {{margin:0 0 0 12px;color:#444;font-size:14px;}}
  /* 可行性思考 - 卡片化 */
  .feas-card {{margin-bottom:16px;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;background:#fff;}}
  .feas-header {{background:#eef2f7;padding:9px 14px;font-weight:600;font-size:14.5px;color:#1a3c5e;border-bottom:2px solid #365772;}}
  .feas-summary {{margin:0;padding:9px 14px 0;font-size:13px;color:#5a6b7b;line-height:1.6;font-style:italic;}}
  .feas-badge {{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;background:#365772;color:#fff;border-radius:50%;font-size:12px;font-weight:bold;margin-right:8px;}}
  .feas-title {{vertical-align:middle;}}
  .feas-list {{margin:0;padding:12px 14px 6px;list-style:none;}}
  .feas-item {{margin-bottom:11px;font-size:14px;line-height:1.6;}}
  .feas-item:last-child {{margin-bottom:4px;}}
  .feas-tag {{display:inline-block;background:#e3eef7;color:#365772;font-size:12px;font-weight:600;padding:2px 8px;border-radius:4px;margin-right:8px;vertical-align:top;}}
  .feas-desc {{color:#444;}}
  .feas-plain {{color:#444;}}
  ul {{padding-left:20px;}}
  a {{color:#d95030;text-decoration:none;}} a:hover {{text-decoration:underline;}}
  @media only screen and (max-width:600px) {{
    .content-table {{width:100%!important;max-width:100%!important;border-radius:0;}}
    .inner-padding {{padding:20px 16px!important;}}
    h1 {{font-size:22px!important;}}
    h2 {{font-size:16px!important;}}
  }}
</style>
</head>
<body>
<table class="wrapper-table" role="presentation" cellspacing="0" cellpadding="0" border="0">
<tr><td align="center" valign="top">
<table class="content-table" role="presentation" cellspacing="0" cellpadding="0" border="0">
<tr><td class="inner-padding">
  <h1>{escape(newsletter.brand_name)}</h1>
  <hr>
  <section>
    <h2>{cfg.overview.icon} {cfg.overview.label}</h2>
    <div class="meta">
      <p><strong>时间范围：</strong>{escape(ov.date_start)} - {escape(ov.date_end)}</p>
      <p><strong>本期编辑：</strong>{escape(ov.editor)}</p>
      <p><strong>核心摘要：</strong>{escape(ov.core_summary)}</p>
    </div>
    {cover_html}
  </section>
  {hot_section}
  <section>
    <h2>{cfg.industry.icon} {cfg.industry.label}</h2>
    {''.join(industry_html)}
  </section>
  {tech_block}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""
