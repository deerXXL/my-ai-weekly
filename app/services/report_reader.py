import json
import re
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"
WEEKLY_JSON_PATTERN = re.compile(r"^weekly-\d{4}-\d{2}-\d{2}\.json$")


def find_latest_report_path() -> Optional[Path]:

    # 优先读取最新报告
    latest = OUTPUT_DIR / "latest.json"

    if latest.exists():
        return latest


    # 如果latest不存在，备用读取weekly文件
    candidates = [
        p for p in OUTPUT_DIR.glob("weekly-*.json")
        if WEEKLY_JSON_PATTERN.match(p.name)
    ]

    if not candidates:
        return None


    return max(
        candidates,
        key=lambda p: p.stem.removeprefix("weekly-")
    )
    

def load_latest_report() -> dict:
    path = find_latest_report_path()
    if path is None:
        return {"date": "", "summary": "", "articles": []}
    print("读取文件:", path)

    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # 如果JSON中没有新字段，从日期反推
    from datetime import datetime, timedelta
    import glob as _glob

    date_str = report.get("date", "")
    period_start = report.get("period_start", "")
    period_end = report.get("period_end", "")

    if (not period_start or not period_end) and date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            period_start = period_start or (d - timedelta(days=14)).strftime("%Y-%m-%d")
            period_end = period_end or date_str
        except ValueError:
            pass

    # 如果没有issue_number，统计已有报告数量作为期号
    issue_number = report.get("issue_number", 0)
    if not issue_number:
        weekly_files = [
            p for p in OUTPUT_DIR.glob("weekly-*.json")
            if WEEKLY_JSON_PATTERN.match(p.name)
        ]
        issue_number = len(weekly_files)

    title = report.get("title", "")
    if not title or title == "AI Daily Report":
        title = f"AI双周产品周报 · 第{issue_number}期"

    return {
        "date": date_str,
        "summary": report.get("summary", ""),
        "title": title,
        "source_file": path.name,
        "issue_number": issue_number,
        "period_start": period_start,
        "period_end": period_end,
        "total_sources": report.get("total_sources", 0),
        "articles": to_frontend_articles(report),
    }


def _extract_date_from_text(text: str) -> str:
    """从标题文本里尝试提取 'Jun 23, 2026' / '2026-07-09' 等日期。"""
    if not text:
        return ""
    from datetime import datetime
    import re

    # 英文格式：Jun 23, 2026
    m = re.search(r"([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", text)
    if m:
        try:
            return datetime.strptime(m.group(1), "%b %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    # 数字格式：2026-07-09 / 2026/07/09
    m = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", text)
    if m:
        try:
            return datetime.strptime(m.group(1).replace("/", "-"), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def to_frontend_articles(report: dict) -> list[dict]:
    """将流水线 signals 转为前端 render.js 所需格式，按发布时间升序排列"""
    articles = []

    # 建立 items 的 URL -> published_at 映射，用于旧报告信号缺失日期时回退
    item_date_map = {}
    for item in report.get("items", []):
        url = item.get("url")
        pub = item.get("published_at")
        if url and pub:
            item_date_map[url] = pub

    for idx, signal in enumerate(report.get("signals", [])):
        category = signal.get("category") or "AI"
        source = signal.get("source") or ""
        tags = [category]
        if source:
            tags.append(source)

        impact = signal.get("impact") or 1
        pub_date = (
            signal.get("published_at")
            or item_date_map.get(signal.get("url"), "")
            or _extract_date_from_text(signal.get("title", ""))
            or ""
        )
        articles.append({
            "idx": idx + 1,
            "title": signal.get("title") or signal.get("signal", ""),
            "tags": tags,
            "date": pub_date,
            "desc": signal.get("insight") or signal.get("signal", ""),
            "hot": impact * 25,
            "impact": impact,
            "link": signal.get("url") or "#",
            "published_at": pub_date,
        })

    # 按发布时间升序（时间线从旧到新）
    articles.sort(key=lambda x: x["published_at"] or "9999-99-99")

    # 重新编号 1..N
    for i, a in enumerate(articles, 1):
        a["idx"] = i
    return articles
