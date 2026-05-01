import feedparser

feeds = {
    "1": ("AI / ML", [
        "https://openai.com/news/rss.xml",
        "https://ai.googleblog.com/feeds/posts/default",
        "https://www.technologyreview.com/feed/",
    ]),
    "2": ("Cybersecurity", [
        "https://krebsonsecurity.com/feed/",
        "https://feeds.feedburner.com/TheHackersNews",
    ]),
    "3": ("Software / Coding", [
        "https://github.blog/feed/",
        "https://stackoverflow.blog/feed/",
        "https://www.smashingmagazine.com/feed/",
    ]),
    "4": ("Technology", [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/index",
    ]),
    "5": ("Finance", [
        "https://www.ft.com/?format=rss",
        "https://feeds.bloomberg.com/markets/news.rss",
    ]),
}

# --- User Input ---
print("Select feed category:")
for key, (name, _) in feeds.items():
    print(f"{key}. {name}")
print("0. Show ALL")

choice = input("Enter your choice: ").strip()
max_items = input("How many items per feed? ").strip()

# Validate inputs
if not max_items.isdigit():
    max_items = 5
else:
    max_items = int(max_items)

# --- Function to display feeds ---
def display_feed(category_name, urls):
    print(f"\n=== {category_name} ===")

    for url in urls:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", url)

        print(f"\nSource: {source}")

        for entry in feed.entries[:max_items]:
            title = entry.get("title", "No title")
            link = entry.get("link", "No link")
            published = entry.get("published", "No date")

            print(f"- {title}")
            print(f"  Date: {published}")
            print(f"  Link: {link}")

# --- Logic ---
if choice == "0":
    for _, (name, urls) in feeds.items():
        display_feed(name, urls)
elif choice in feeds:
    name, urls = feeds[choice]
    display_feed(name, urls)
else:
    print("Invalid choice. Showing ALL feeds instead.")
    for _, (name, urls) in feeds.items():
        display_feed(name, urls)