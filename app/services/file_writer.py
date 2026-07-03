import json
import os
from dataclasses import asdict


def write_markdown(report):
    """
    输出 Markdown 日报
    """
    os.makedirs("output", exist_ok=True)

    filename = f"output/weekly-{report.date}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {report.title}\n\n")

        f.write(f"**Date:** {report.date}\n\n")

        f.write("## Summary\n\n")
        f.write(report.summary + "\n\n")

        f.write("## AI Signals\n\n")

        for i, signal in enumerate(report.signals, 1):
            f.write(f"### {i}. {signal.title}\n")
            f.write(f"- Signal: {signal.signal}\n")
            f.write(f"- Insight: {signal.insight}\n")
            f.write(f"- Category: {signal.category}\n")
            f.write(f"- Impact: {signal.impact}\n")
            f.write(f"- URL: {signal.url}\n\n")

    print(f"✅ Markdown 已生成：{filename}")


def write_json(report):
    """
    输出 JSON，供 Web / API / Notion 使用
    """
    os.makedirs("output", exist_ok=True)

    filename = f"output/weekly-{report.date}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            asdict(report),
            f,
            ensure_ascii=False,
            indent=4
        )

    print(f"✅ JSON 已生成：{filename}")