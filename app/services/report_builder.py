import json
from datetime import datetime, timedelta
from pathlib import Path

from app.models.daily_report import (
    IndustryNewsItem,
    OverviewBlock,
    WeeklyNewsletter,
)


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


def build_report(items, signals, days=14):
    """将 SignalCard 列表转换为 WeeklyNewsletter（兼容旧调用入口）。

    Args:
        items: RawItem 列表（旧接口保留，暂未使用）
        signals: SignalCard 列表
        days: 覆盖天数

    Returns:
        WeeklyNewsletter 实例
    """
    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    period_start, period_end = _calc_period(days)
    issue_number = _calc_issue_number()

    # 统计数据源
    sources = set()
    for s in signals:
        if s.source:
            sources.add(s.source)
    total_sources = len(sources)

    # 将 SignalCard 转为 IndustryNewsItem
    industry_news = [
        IndustryNewsItem(
            date_label=period_start,
            title=s.title or s.signal,
            summary=s.insight,
            url=s.url,
            image_url="",
            usage_note="",
        )
        for s in signals
    ]

    # 生成核心摘要
    if signals:
        top3 = sorted(signals, key=lambda x: x.impact, reverse=True)[:3]
        top_titles = " / ".join(s.title for s in top3 if s.title)
        core_summary = (
            f"本期（第{issue_number}期）覆盖 {period_start} 至 {period_end}，"
            f"共抓取 {total_sources} 个数据源，"
            f"筛选出 {len(signals)} 条AI信号。"
            f"重点关注：{top_titles}"
        )
    else:
        core_summary = "本周期未发现显著AI信号。"

    return WeeklyNewsletter(
        brand_name="闪联AI周刊",
        overview=OverviewBlock(
            date_start=period_start,
            date_end=period_end,
            editor="产品资讯组",
            core_summary=core_summary,
        ),
        industry_news=industry_news,
        generated_at=generated_at,
        issue_number=issue_number,
        period_start=period_start,
        period_end=period_end,
        total_sources=total_sources,
    )
