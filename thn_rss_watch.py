#!/usr/bin/env python3
"""
Track The Hacker News RSS feeds with:
- time range filtering
- real-time watching
- flexible intervals
- configurable number of feeds/posts

Install:
  python -m venv .venv
  .venv\Scripts\activate (or) replace the `python` everytime to `.venv\Scripts\python.exe`
  pip install feedparser tzdata

Examples:
  python thn_rss_watch.py --since 24h
  python thn_rss_watch.py --since 2026-05-01 --until 2026-05-09
  python thn_rss_watch.py --watch --interval 30 --interval-unit seconds
  python thn_rss_watch.py --watch --interval 10 --interval-unit minutes
  python thn_rss_watch.py --max-posts 5
  python thn_rss_watch.py --max-feeds 1
"""

import argparse
import calendar
import hashlib
import re
import sqlite3
import time
from datetime import datetime, date, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo

import feedparser


DEFAULT_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://thehackernews.com/feeds/posts/default?alt=rss",
]

DB_FILE = "thn_seen_posts.sqlite3"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat(timespec="seconds")


def get_timezone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:
        print(f"[WARN] Invalid timezone '{tz_name}', falling back to UTC.")
        return ZoneInfo("UTC")


def parse_time_value(value: str | None, tz: ZoneInfo, boundary: str) -> datetime | None:
    if not value:
        return None

    value = value.strip()

    if value.lower() == "now":
        return datetime.now(tz).astimezone(timezone.utc)

    relative_match = re.fullmatch(
        r"(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)",
        value.lower(),
    )

    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)

        if unit.startswith("s"):
            delta = timedelta(seconds=amount)
        elif unit.startswith("m"):
            delta = timedelta(minutes=amount)
        elif unit.startswith("h") or unit.startswith("hr"):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(days=amount)

        return (datetime.now(tz) - delta).astimezone(timezone.utc)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        parsed_date = date.fromisoformat(value)

        if boundary == "start":
            parsed_dt = datetime.combine(parsed_date, dt_time.min)
        else:
            parsed_dt = datetime.combine(parsed_date, dt_time.max)

        return parsed_dt.replace(tzinfo=tz).astimezone(timezone.utc)

    try:
        parsed_dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=tz)

        return parsed_dt.astimezone(timezone.utc)

    except ValueError as exc:
        raise ValueError(
            f"Invalid time value: {value}. "
            "Use YYYY-MM-DD, ISO datetime, now, or relative values like 30m, 12h, 7d."
        ) from exc


def interval_to_seconds(amount: int, unit: str) -> int:
    unit = unit.lower()

    multipliers = {
        "seconds": 1,
        "second": 1,
        "secs": 1,
        "sec": 1,
        "s": 1,
        "minutes": 60,
        "minute": 60,
        "mins": 60,
        "min": 60,
        "m": 60,
        "hours": 3600,
        "hour": 3600,
        "hrs": 3600,
        "hr": 3600,
        "h": 3600,
        "days": 86400,
        "day": 86400,
        "d": 86400,
    }

    if amount <= 0:
        raise ValueError("Interval must be greater than zero.")

    if unit not in multipliers:
        raise ValueError("Interval unit must be seconds, minutes, hours, or days.")

    return amount * multipliers[unit]


def validate_optional_positive_int(value: int | None, name: str) -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_posts (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            feed_url TEXT,
            published_utc TEXT,
            first_seen_utc TEXT
        )
        """
    )

    conn.commit()
    return conn


def entry_datetime(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")

    if not parsed:
        return None

    timestamp = calendar.timegm(parsed)
    return datetime.fromtimestamp(timestamp, timezone.utc)


def post_id(entry) -> str:
    raw = (
        entry.get("link")
        or entry.get("id")
        or entry.get("guid")
        or f"{entry.get('title', '')}-{entry.get('published', '')}"
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def already_seen(conn: sqlite3.Connection, item_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen_posts WHERE id = ?",
        (item_id,),
    ).fetchone()

    return row is not None


def save_seen(
    conn: sqlite3.Connection,
    item_id: str,
    title: str,
    link: str,
    feed_url: str,
    published_utc: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO seen_posts
        (id, title, link, feed_url, published_utc, first_seen_utc)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, title, link, feed_url, published_utc, now_iso()),
    )

    conn.commit()


def within_time_range(
    published_dt: datetime | None,
    since_dt: datetime | None,
    until_dt: datetime | None,
    include_undated: bool,
) -> bool:
    if published_dt is None:
        return include_undated

    if since_dt and published_dt < since_dt:
        return False

    if until_dt and published_dt > until_dt:
        return False

    return True


def fetch_posts(
    conn: sqlite3.Connection,
    feed_urls: list[str],
    since_dt: datetime | None,
    until_dt: datetime | None,
    include_undated: bool,
    save_only: bool = False,
    max_posts: int | None = None,
    max_per_feed: int | None = None,
) -> list[dict]:
    posts = []

    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)

        if feed.bozo:
            print(f"[WARN] Could not fully parse feed: {feed_url}")
            if feed.bozo_exception:
                print(f"       {feed.bozo_exception}")

        entries = feed.entries

        if max_per_feed is not None:
            entries = entries[:max_per_feed]

        for entry in entries:
            item_id = post_id(entry)
            title = entry.get("title", "Untitled")
            link = entry.get("link", "")
            published_dt = entry_datetime(entry)
            published_utc = published_dt.isoformat(timespec="seconds") if published_dt else ""

            if not within_time_range(published_dt, since_dt, until_dt, include_undated):
                continue

            if already_seen(conn, item_id):
                continue

            save_seen(conn, item_id, title, link, feed_url, published_utc)

            if save_only:
                continue

            posts.append(
                {
                    "title": title,
                    "link": link,
                    "feed": feed_url,
                    "published_utc": published_utc,
                }
            )

    posts.sort(key=lambda item: item["published_utc"] or "", reverse=True)

    if max_posts is not None:
        posts = posts[:max_posts]

    return posts


def print_posts(posts: list[dict]) -> None:
    if not posts:
        print(f"[{now_iso()}] No new matching posts.")
        return

    print(f"[{now_iso()}] Found {len(posts)} new matching post(s):\n")

    for post in posts:
        print(f"- {post['title']}")

        if post["published_utc"]:
            print(f"  Published UTC: {post['published_utc']}")

        print(f"  Link: {post['link']}")
        print(f"  Feed: {post['feed']}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Track The Hacker News RSS feeds by time range or in real time."
    )

    parser.add_argument(
        "--db",
        default=DB_FILE,
        help=f"SQLite database file. Default: {DB_FILE}",
    )

    parser.add_argument(
        "--feed",
        action="append",
        help="Add a feed URL. Can be used multiple times.",
    )

    parser.add_argument(
        "--max-feeds",
        type=int,
        default=None,
        help="Maximum number of feed URLs to fetch.",
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum total number of new posts to return per check.",
    )

    parser.add_argument(
        "--max-per-feed",
        type=int,
        default=None,
        help="Maximum number of RSS entries to read from each feed URL.",
    )

    parser.add_argument(
        "--since",
        help="Start time. Examples: 2026-05-01, 2026-05-01T12:00:00+08:00, 24h, 7d",
    )

    parser.add_argument(
        "--until",
        help="End time. Examples: 2026-05-09, now, 2h",
    )

    parser.add_argument(
        "--timezone",
        default="Asia/Kuala_Lumpur",
        help="Timezone for date-only or timezone-less inputs. Default: Asia/Kuala_Lumpur",
    )

    parser.add_argument(
        "--include-undated",
        action="store_true",
        help="Include feed entries that have no published or updated timestamp.",
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously track new posts.",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Update interval amount. Default: 15",
    )

    parser.add_argument(
        "--interval-unit",
        default="minutes",
        choices=[
            "seconds", "second", "secs", "sec", "s",
            "minutes", "minute", "mins", "min", "m",
            "hours", "hour", "hrs", "hr", "h",
            "days", "day", "d",
        ],
        help="Update interval unit. Default: minutes",
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="When watching, mark current matching posts as seen before tracking begins.",
    )

    args = parser.parse_args()

    validate_optional_positive_int(args.max_feeds, "--max-feeds")
    validate_optional_positive_int(args.max_posts, "--max-posts")
    validate_optional_positive_int(args.max_per_feed, "--max-per-feed")

    tz = get_timezone(args.timezone)
    since_dt = parse_time_value(args.since, tz, boundary="start")
    until_dt = parse_time_value(args.until, tz, boundary="end")
    sleep_seconds = interval_to_seconds(args.interval, args.interval_unit)

    if since_dt and until_dt and since_dt > until_dt:
        raise ValueError("--since must be earlier than --until.")

    feeds = args.feed if args.feed else DEFAULT_FEEDS

    if args.max_feeds is not None:
        feeds = feeds[:args.max_feeds]

    conn = init_db(args.db)

    print("Tracking feeds:")
    for feed_url in feeds:
        print(f"  - {feed_url}")

    if args.max_feeds:
        print(f"Maximum feed URLs: {args.max_feeds}")

    if args.max_per_feed:
        print(f"Maximum entries per feed: {args.max_per_feed}")

    if args.max_posts:
        print(f"Maximum new posts per check: {args.max_posts}")

    if since_dt:
        print(f"Since UTC: {since_dt.isoformat(timespec='seconds')}")

    if until_dt:
        print(f"Until UTC: {until_dt.isoformat(timespec='seconds')}")

    if args.watch:
        print("Watch mode: enabled")
        print(f"Update interval: {args.interval} {args.interval_unit}")

    print()

    try:
        if args.watch and args.skip_existing:
            print(f"[{now_iso()}] Marking existing matching posts as seen...")

            fetch_posts(
                conn=conn,
                feed_urls=feeds,
                since_dt=since_dt,
                until_dt=until_dt,
                include_undated=args.include_undated,
                save_only=True,
                max_posts=args.max_posts,
                max_per_feed=args.max_per_feed,
            )

            print(f"[{now_iso()}] Real-time tracking started.\n")

        while True:
            posts = fetch_posts(
                conn=conn,
                feed_urls=feeds,
                since_dt=since_dt,
                until_dt=until_dt,
                include_undated=args.include_undated,
                max_posts=args.max_posts,
                max_per_feed=args.max_per_feed,
            )

            print_posts(posts)

            if not args.watch:
                break

            time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()