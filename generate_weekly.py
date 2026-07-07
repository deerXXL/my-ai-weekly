from app.crawlers.github_trending import fetch_github_trending

from app.services.llm_signal import generate_signal

from app.services.report_generator import save_report


def main():

    print("🚀 开始生成AI双周周报...")


    # 1.抓取资讯

    items = fetch_github_trending()


    print(
        f"📌 抓取到 {len(items)} 条资讯"
    )


    # 2.AI分析

    cards = []


    for item in items:

        print(
            "🤖 AI分析:",
            item.title
        )


        card = generate_signal(item)

        cards.append(card)



    # 3.生成网页JSON

    save_report(cards)



    print("✅ 周报生成完成")



if __name__ == "__main__":

    main()