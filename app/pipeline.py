from app.crawlers.github_trending import fetch_github_trending
from app.crawlers.openai_blog import fetch_openai_blog
from app.services.llm_signal import generate_signal
from app.services.report_builder import build_report
from app.services.filter import filter_items

def run_pipeline():
    """
    AI日报主流程
    """

    # 1️⃣ 数据源
    from app.crawlers.registry import load_all_sources

    items = load_all_sources()

# 数据过滤
    items = filter_items(items)

    print(f"过滤后共有 {len(items)} 条资讯")

    print(f"📦 数据总量: {len(items)}")

    # 2️⃣ LLM分析
    results = []

    for item in items:
        print("➡️ 分析:", item.title)
        try:
            results.append(generate_signal(item))
        except Exception as e:
            print("❌ error:", e)

    # 3️⃣ 排序
    results = sorted(results, key=lambda x: x.impact, reverse=True)

    # 4️⃣ 构建报告
    report = build_report(
        items=items,
        signals=results
    )

    return report