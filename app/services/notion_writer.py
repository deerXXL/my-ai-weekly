from notion_client import Client


NOTION_TOKEN = "你的NOTION_TOKEN"
DATABASE_ID = "你的DATABASE_ID"

notion = Client(auth=NOTION_TOKEN)


def write_signal(signal):
    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": signal.title
                        }
                    }
                ]
            },
            "Signal": {
                "rich_text": [
                    {
                        "text": {
                            "content": signal.signal
                        }
                    }
                ]
            },
            "Insight": {
                "rich_text": [
                    {
                        "text": {
                            "content": signal.insight
                        }
                    }
                ]
            },
            "Category": {
                "rich_text": [
                    {
                        "text": {
                            "content": signal.category
                        }
                    }
                ]
            },
            "Impact": {
                "number": signal.impact
            },
            "URL": {
                "url": signal.url
            }
        }
    )