import json
from pathlib import Path
from datetime import datetime

from app.models.signal_card import SignalCard



def signal_to_report(card: SignalCard):

    return {

        "title":
        card.title or card.signal,


        "tags":[
            card.category,
            card.source
        ],


        "date":
        datetime.now().strftime("%Y-%m-%d"),


        "desc":
        card.insight,


        "hot":
        card.impact,


        "link":
        card.url

    }



def save_report(cards):

    data = [
        signal_to_report(card)
        for card in cards
    ]


    path = Path(
        "output/weekly_report.json"
    )


    path.parent.mkdir(
        exist_ok=True
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


    print(
        "✅ 周报生成完成:",
        path
    )