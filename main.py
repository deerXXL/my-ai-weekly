"""闪联AI周刊 — 唯一入口：生成周刊并启动本地 HTML 预览服务。"""
import argparse
import os

from app.pipeline import run_pipeline
from app.services.issue_paths import issue_name
from web_server import app


def main():
    parser = argparse.ArgumentParser(description="闪联AI周刊：生成 + 本地预览")
    parser.add_argument(
        "--serve-only",
        action="store_true",
        help="跳过生成，仅启动本地 HTML 预览服务",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    if not args.serve_only:
        print("=" * 50)
        print("闪联AI周刊 — 开始生成")
        print("=" * 50)
        newsletter = run_pipeline()
        print("\n生成完成:")
        print(f"  行业动态: {len(newsletter.industry_news)} 条")
        if newsletter.tech_summary:
            print(f"  核心趋势: {len(newsletter.tech_summary.trends)} 条")
        print(f"  输出目录: output/{issue_name(newsletter.generated_at[:10])}/")

    print("\n" + "=" * 50)
    print(f"本地预览: http://{args.host}:{args.port}/")
    print("=" * 50 + "\n")

    app.run(
        host=args.host,
        port=args.port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
