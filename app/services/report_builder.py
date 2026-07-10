import json
from datetime import datetime, timedelta
from pathlib import Path

from app.models.daily_report import DailyReport


BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"


def _calc_issue_number() -> int:
    """统计已有报告数，返回下一期号"""
    count = 0
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.glob("weekly-*.json"):
            if f.name != "latest.json":
                count += 1
    return count + 1


def _calc_period(days: int = 14):
    """计算双周统计区间"""
    now = datetime.now()
    period_end = now.strftime("%Y-%m-%d")
    period_start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    return period_start, period_end


def _calc_total_sources(items):
    """统计去重后的数据源数量"""
    sources = set()
    for item in items:
        if item.source:
            sources.add(item.source)
    return len(sources)


def build_report(items, signals, days=14):
    """生成双周报告"""
    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    period_start, period_end = _calc_period(days)
    issue_number = _calc_issue_number()
    total_sources = _calc_total_sources(items)

    if not signals:
        return DailyReport(
            date=report_date,
            title=f"AI双周产品周报 · 第{issue_number}期",
            summary="本周期未发现显著AI信号。",
            signals=[],
            items=items,
            github_projects=[],
            generated_at=generated_at,
            issue_number=issue_number,
            period_start=period_start,
            period_end=period_end,
            total_sources=total_sources,
        )

    # 按impact排序取top信号
    sorted_signals = sorted(signals, key=lambda x: x.impact, reverse=True)
    top3 = sorted_signals[:3]
    top_titles = " / ".join(s.title for s in top3 if s.title)

    summary = (
        f"本期（第{issue_number}期）覆盖 {period_start} 至 {period_end}，"
        f"共抓取 {total_sources} 个数据源，"
        f"筛选出 {len(signals)} 条AI信号。"
        f"重点关注：{top_titles}"
    )

    return DailyReport(
        date=report_date,
        title=f"AI双周产品周报 · 第{issue_number}期",
        summary=summary,
        items=items,
        signals=signals,
        github_projects=[],
        generated_at=generated_at,
        issue_number=issue_number,
        period_start=period_start,
        period_end=period_end,
        total_sources=total_sources,
    )