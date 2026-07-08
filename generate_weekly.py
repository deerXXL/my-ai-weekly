from app.pipeline import run_pipeline
from app.services.file_writer import write_json, write_markdown


def main():
    print("Starting AI weekly report generation...")
    report = run_pipeline()
    write_markdown(report)
    write_json(report)
    print("Weekly report generated.")


if __name__ == "__main__":
    main()
