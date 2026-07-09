import json
import shutil
import os
from dataclasses import asdict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

OUTPUT_DIR = BASE_DIR / "output"


def write_markdown(report):
    """Write a Markdown report."""
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

    print(f"Markdown generated: {filename}")


def write_json(report):
    """Write JSON for Web/API/Notion consumers."""

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    filename = OUTPUT_DIR / f"weekly-{report.date}.json"


    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            asdict(report),
            f,
            ensure_ascii=False,
            indent=4,
        )


    # 更新 latest.json

    shutil.copy(
        filename,
        OUTPUT_DIR / "latest.json"
    )


    print(
        f"JSON generated: {filename}"
    )