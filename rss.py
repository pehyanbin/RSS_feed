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

# CLI colours
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"

print(f"{BOLD}{CYAN}Select feed category:{RESET}")
for key, (name, _) in feeds.items():
    print(f"{YELLOW}{key}.{RESET} {name}")
print(f"{YELLOW}0.{RESET} Show ALL")

choice = input(f"\n{GREEN}Enter your choice: {RESET}").strip()
max_items = input(f"{GREEN}How many items per feed? {RESET}").strip()

if not max_items.isdigit():
    max_items = 5
else:
    max_items = int(max_items)

def display_feed(category_name, urls):
    print(f"\n{BOLD}{CYAN}=== {category_name} ==={RESET}")

    for url in urls:
        feed = feedparser.parse(url)
        source = feed.feed.get("title", url)

        print(f"\n{BOLD}{BLUE}Source: {source}{RESET}")

        for index, entry in enumerate(feed.entries[:max_items], start=1):
            title = entry.get("title", "No title")
            link = entry.get("link", "No link")
            published = entry.get("published", "No date")

            print(f"{YELLOW}{index}.{RESET} {BOLD}{title}{RESET}")
            print(f"   {GREEN}Date:{RESET} {published}")
            print(f"   {YELLOW}Link:{RESET} {YELLOW}{link}{RESET}")

if choice == "0":
    for _, (name, urls) in feeds.items():
        display_feed(name, urls)
elif choice in feeds:
    name, urls = feeds[choice]
    display_feed(name, urls)
else:
    print(f"{RED}Invalid choice. Showing ALL feeds instead.{RESET}")
    for _, (name, urls) in feeds.items():
        display_feed(name, urls)