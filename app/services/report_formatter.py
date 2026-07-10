from datetime import datetime


def signal_to_report(card):

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