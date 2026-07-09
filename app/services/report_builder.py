from datetime import datetime

from app.models.daily_report import DailyReport


def build_report(items, signals):
    """Wrap SignalCard records into a DailyReport."""
    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")

    if not signals:
        return DailyReport(
            date=report_date,
            title="AI Daily Report",
            summary="No AI signals found today.",
            signals=[],
            items=items,
            github_projects=[],
            generated_at=generated_at,
        )

    summary = (
        f"Today we found {len(signals)} AI signals. "
        f"The most important signal is: {signals[0].signal}"
    )

    return DailyReport(
        date=report_date,
        title="AI Daily Report",
        summary=summary,
        items=items,
        signals=signals,
        github_projects=[],
        generated_at=generated_at,
    )
