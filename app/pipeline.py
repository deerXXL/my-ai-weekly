from datetime import datetime
from app.crawlers.registry import load_all_sources
from app.services.filter import filter_items
from app.services.llm_signal import generate_signal
from app.services.report_builder import build_report
from app.services.file_writer import write_json, write_markdown


def _sort_items_by_date(items):
    """按发布时间升序排列（无日期的排在最后）"""
    def _key(item):
        if item.published_at:
            try:
                return datetime.strptime(item.published_at, "%Y-%m-%d")
            except (ValueError, TypeError):
                pass
        return datetime.max
    return sorted(items, key=_key)


def run_pipeline(days=14, mode="practical"):
    """Main AI daily report pipeline."""
    items = load_all_sources()
    items = filter_items(items, days=days, mode=mode)

    # 按时间线排序后再生成信号（前端按时间线展示）
    items = _sort_items_by_date(items)

    print(f"Items after filtering: {len(items)}")
    print(f"Total items: {len(items)}")

    signals = []
    for item in items:
        print("Analyzing:", item.title)
        try:
            signals.append(generate_signal(item))
        except Exception as exc:
            print("Signal generation error:", exc)

    signals = sorted(signals, key=lambda x: x.impact, reverse=True)

    report = build_report(
        items=items,
        signals=signals,
        days=days,
    )

    # ✅ 写文件:JSON 给前端/Markdown 给人看
    write_json(report)
    write_markdown(report)
    print(f"Pipeline finished. signals={len(signals)}")
    return report
