import feedparser

feeds = {
    "AI / ML": [
        "https://openai.com/news/rss.xml",
        "https://ai.googleblog.com/feeds/posts/default",
        "https://www.technologyreview.com/feed/",
    ],
    "Cybersecurity": [
        "https://krebsonsecurity.com/feed/",
        "https://feeds.feedburner.com/TheHackersNews",
    ],
    "Software / Coding": [
        "https://github.blog/feed/",
        "https://stackoverflow.blog/feed/",
        "https://www.smashingmagazine.com/feed/",
    ],
    "Technology": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "Finance": [
        "https://www.ft.com/?format=rss",
        "https://feeds.bloomberg.com/markets/news.rss",
    ],
}

MAX_ITEMS = 5

for category, urls in feeds.items():
    print(f"\n=== {category} ===")

    for url in urls:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", url)

        print(f"\nSource: {source}")

        for entry in feed.entries[:MAX_ITEMS]:
            title = entry.get("title", "No title")
            link = entry.get("link", "No link")
            published = entry.get("published", "No date")

            print(f"- {title}")
            print(f"  Date: {published}")
            print(f"  Link: {link}")