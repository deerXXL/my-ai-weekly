import json
import re
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path("output")
WEEKLY_JSON_PATTERN = re.compile(r"^weekly-\d{4}-\d{2}-\d{2}\.json$")


def find_latest_report_path() -> Optional[Path]:
    """返回 output/ 下最新的 weekly-YYYY-MM-DD.json。"""
    candidates = [
        p for p in OUTPUT_DIR.glob("weekly-*.json")
        if WEEKLY_JSON_PATTERN.match(p.name)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stem.removeprefix("weekly-"))


def load_latest_report() -> dict:
    path = find_latest_report_path()
    if path is None:
        return {"date": "", "summary": "", "articles": []}

    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)

    return {
        "date": report.get("date", ""),
        "summary": report.get("summary", ""),
        "title": report.get("title", ""),
        "source_file": path.name,
        "articles": to_frontend_articles(report),
    }


def to_frontend_articles(report: dict) -> list[dict]:
    """将流水线 signals 转为前端 render.js 所需格式。"""
    date = report.get("date", "")
    articles = []

    for signal in report.get("signals", []):
        category = signal.get("category") or "AI"
        source = signal.get("source") or ""
        tags = [category]
        if source:
            tags.append(source)

        articles.append({
            "title": signal.get("title") or signal.get("signal", ""),
            "tags": tags,
            "date": date,
            "desc": signal.get("insight") or signal.get("signal", ""),
            "hot": (signal.get("impact") or 1) * 25,
            "link": signal.get("url") or "#",
        })

    articles.sort(key=lambda x: x["hot"], reverse=True)
    return articles
