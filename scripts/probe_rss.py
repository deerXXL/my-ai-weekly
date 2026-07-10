"""Probe domestic RSS feeds for availability and freshness."""
import feedparser
from datetime import datetime, timezone

FEEDS = {
    "机器之心": "https://www.jiqizhixin.com/rss",
    "量子位官网": "https://www.qbitai.com/feed",
    "量子位RSSHub": "https://rsshub.app/qbitai",
    "雷锋网AI": "https://www.leiphone.com/feed/categoryRss/name/ai",
    "雷锋网早报": "https://www.leiphone.com/feed/categoryRss/name/zaobao",
    "IT之家": "https://www.ithome.com/rss/",
    "36氪": "https://36kr.com/feed-article",
    "InfoQ-RSSHub": "https://rsshub.app/infoq/topic/1",
    "虎嗅": "https://www.huxiu.com/rss/0.xml",
    "钛媒体": "https://www.tmtpost.com/rss.xml",
    "智东西": "https://www.zhidx.com/rss",
    "少数派": "https://sspai.com/feed",
    "开源中国": "https://www.oschina.net/news/rss",
    "AIbase": "https://www.aibase.com/zh/news/rss",
}

print(f"{'source':<16} {'status':<10} {'count':<5} {'latest':<12} {'fresh':<6} title")
print("-" * 95)
for name, url in FEEDS.items():
    try:
        d = feedparser.parse(url)
        status = d.get("status", "ok") or "ok"
        if d.bozo and not d.entries:
            status = f"err:{type(d.bozo_exception).__name__[:10]}"
        entries = d.entries[:20]
        count = len(entries)
        latest = "-"
        fresh = "?"
        title = "-"
        if entries:
            e = entries[0]
            title = (e.get("title") or "-")[:45]
            pub = e.get("published_parsed") or e.get("updated_parsed")
            if pub:
                dt = datetime(*pub[:6], tzinfo=timezone.utc)
                latest = dt.strftime("%Y-%m-%d")
                age = (datetime.now(timezone.utc) - dt).days
                fresh = "yes" if age <= 2 else ("ok" if age <= 7 else "slow")
        print(f"{name:<16} {str(status):<10} {count:<5} {latest:<12} {fresh:<6} {title}")
    except Exception as ex:
        print(f"{name:<16} ERR        -     -            {str(ex)[:35]}")
