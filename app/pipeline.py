from app.crawlers.registry import load_all_sources
from app.services.filter import filter_items
from app.services.llm_signal import generate_signal
from app.services.report_builder import build_report
from app.services.file_writer import write_json, write_markdown


def run_pipeline():
    """Main AI daily report pipeline."""
    items = load_all_sources()
    items = filter_items(items)

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
    )

    # ✅ 写文件:JSON 给前端/Markdown 给人看
    write_json(report)
    write_markdown(report)
    print(f"Pipeline finished. signals={len(signals)}")
    return report
