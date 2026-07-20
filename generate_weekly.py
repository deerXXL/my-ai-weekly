import argparse
from app.pipeline import run_pipeline
from app.services.file_writer import write_json, write_markdown, write_html


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
    write_html(report)
    write_markdown(report)
    write_json(report)
    print("Weekly report generated.")

    # 生成完成后按日期重排所有期号，确保连续（定期删除后不留空档，
    # 例如删掉最旧一期后，剩余期自动变为 1、2、3…）
    from app.services.retention import renumber_all_issues
    try:
        n = renumber_all_issues()
        print(f"期刊期号已按日期重排，当前共 {n} 期")
    except Exception as e:
        print(f"⚠️ 期号重排跳过：{e}")


if __name__ == "__main__":
    main()
