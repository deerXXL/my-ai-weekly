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

    return {
        "date": report.get("date", ""),
        "summary": report.get("summary", ""),
        "title": report.get("title", ""),
        "source_file": path.name,
        "issue_number": report.get("issue_number", 0),
        "period_start": report.get("period_start", ""),
        "period_end": report.get("period_end", ""),
        "total_sources": report.get("total_sources", 0),
        "articles": to_frontend_articles(report),
    }


def to_frontend_articles(report: dict) -> list[dict]:
    """将流水线 signals 转为前端 render.js 所需格式。"""
    date = report.get("date", "")
    articles = []

    for idx, signal in enumerate(report.get("signals", [])):
        category = signal.get("category") or "AI"
        source = signal.get("source") or ""
        tags = [category]
        if source:
            tags.append(source)

        impact = signal.get("impact") or 1
        articles.append({
            "idx": idx + 1,
            "title": signal.get("title") or signal.get("signal", ""),
            "tags": tags,
            "date": date,
            "desc": signal.get("insight") or signal.get("signal", ""),
            "hot": impact * 25,
            "impact": impact,
            "link": signal.get("url") or "#",
        })

    articles.sort(key=lambda x: x["impact"], reverse=True)
    # 重新编号 1..N
    for i, a in enumerate(articles, 1):
        a["idx"] = i
    return articles
