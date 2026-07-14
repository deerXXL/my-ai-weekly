import argparse
from app.pipeline import run_pipeline
from app.services.file_writer import write_json, write_markdown


def main():
    parser = argparse.ArgumentParser(description="Generate AI weekly report")
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Filter items published within the last N days (default: 14)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="practical",
        choices=["practical", "strict"],
        help="Date filtering mode: 'practical' keeps undated items with penalty, 'strict' drops them (default: practical)"
    )
    args = parser.parse_args()

    print(f"Starting AI weekly report generation... (days={args.days}, mode={args.mode})")
    report = run_pipeline()
    write_markdown(report)
    write_json(report)
    print("Weekly report generated.")


if __name__ == "__main__":
    main()
