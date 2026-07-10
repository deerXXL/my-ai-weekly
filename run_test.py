from app.pipeline import run_pipeline
from app.services.file_writer import write_markdown, write_json


def main():
    print("\nAI weekly report generation started...\n")

    report = run_pipeline()

    print("\nReport overview:")
    print(f"  Brand:     {report.brand_name}")
    print(f"  Date:      {report.date}")
    print(f"  Period:    {report.overview.date_start} ~ {report.overview.date_end}")
    print(f"  Editor:    {report.overview.editor}")
    print(f"  Summary:   {report.overview.core_summary}")

    print(f"\nIndustry news ({len(report.industry_news)} items):\n")
    for item in report.industry_news[:3]:
        print(f"  Title:   {item.title}")
        print(f"  Summary: {item.summary}")
        print(f"  Date:    {item.date_label}")
        print("-" * 50)

    write_markdown(report)
    write_json(report)


if __name__ == "__main__":
    main()
