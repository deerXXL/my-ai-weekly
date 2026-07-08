from app.pipeline import run_pipeline
from app.services.file_writer import write_markdown, write_json


def main():
    print("\nAI daily report generation started...\n")

    report = run_pipeline()

    print("\nReport summary:")
    print(report.summary)

    print("\nTop signals:\n")
    for signal in report.signals[:3]:
        print("Signal:", signal.signal)
        print("Insight:", signal.insight)
        print("Category:", signal.category)
        print("Impact:", signal.impact)
        print("-" * 50)

    write_markdown(report)
    write_json(report)


if __name__ == "__main__":
    main()
