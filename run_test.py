from app.pipeline import run_pipeline
from app.services.file_writer import write_markdown, write_json


def main():
    print("\n🚀 V3 AI日报生成开始...\n")

    report = run_pipeline()

    print("\n📊 日报摘要:")
    print(report.summary)

    print("\n🔥 TOP SIGNALS:\n")

    for s in report.signals[:3]:
        print("🔥", s.signal)
        print("💡", s.insight)
        print("🏷", s.category)
        print("⭐", s.impact)
        print("-" * 50)

    write_markdown(report)
    write_json(report)


if __name__ == "__main__":
    main()