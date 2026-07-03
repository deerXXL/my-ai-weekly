from datetime import datetime

from app.models.daily_report import DailyReport


def build_report(items, signals):
    """
    将 SignalCard 列表封装成 DailyReport
    """

    if not signals:
        return DailyReport(
            date=...,
            title="AI Daily Report",
            summary="No AI signals found today.",
            signals=[],
            items=[],
            github_projects=[],
            generated_at=...
)

    summary = (
        f"Today we found {len(signals)} AI signals. "
        f"The most important signal is: {signals[0].signal}"
    )

    return DailyReport(
        date=datetime.now().strftime("%Y-%m-%d"),
        title="AI Daily Report",
        summary=summary,
        items=items,
        signals=signals,
        github_projects=[],
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)