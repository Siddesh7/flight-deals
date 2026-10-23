#!/usr/bin/env python3
"""Forward hand-picked deals from US deal blogs to Telegram.

Polls WordPress deal blogs (escape.flights and its sister sites) for new posts and
forwards the ones whose destination matches a keyword in config.json, so US
domestic and Hawaii posts are skipped.
"""

import html
import json
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

from deals import CONFIG, HERE, http_get_json, load_json, save_json, send_telegram

SEEN = HERE / "data" / "blog_seen.json"


def keywords(config):
    """Destination names from the regions plus the extra blog keywords."""
    words = set(config["blogs"]["extra_keywords"])
    for region, spec in config["regions"].items():
        if region in config["blogs"]["skip_regions"]:
            continue
        for name in spec["destinations"].values():
            words.add(name.split("(")[0].split(",")[0].strip())
    return {w.lower() for w in words if w}


def destination_part(title):
    """'Cheap Flights: Los Angeles to Singapore $313...' -> 'Singapore'."""
    m = re.search(r"\bto(?:/from)?\s+(.*?)\s*\$", title)
    return m.group(1) if m else title


def matches(title, words):
    dest = destination_part(title).lower()
    return any(re.search(rf"\b{re.escape(w)}\b", dest) for w in words)


def fetch_posts(site):
    query = urllib.parse.urlencode({"per_page": 50, "_fields": "id,date_gmt,title,link"})
    return http_get_json(f"https://{site}/wp-json/wp/v2/posts?{query}") or []


def main():
    config = load_json(CONFIG, None)
    blogs = config["blogs"]
    words = keywords(config)
    seen = load_json(SEEN, {})
    cutoff = datetime.now(timezone.utc) - timedelta(hours=blogs["max_age_hours"])

    sent = 0
    for site in blogs["sites"]:
        site_seen = set(seen.get(site, []))
        posts = fetch_posts(site)
        for post in reversed(posts):  # oldest first
            if post["id"] in site_seen:
                continue
            site_seen.add(post["id"])
            posted = datetime.fromisoformat(post["date_gmt"]).replace(tzinfo=timezone.utc)
            title = html.unescape(post["title"]["rendered"])
            if posted < cutoff or not matches(title, words):
                continue
            send_telegram(f"📰 <b>{html.escape(title)}</b>\n"
                          f'<a href="{post["link"]}">Read on {site}</a>')
            sent += 1
        # Keep only ids the site still lists, so the file doesn't grow forever.
        listed = {p["id"] for p in posts}
        seen[site] = sorted(site_seen & listed) if listed else sorted(site_seen)

    print(f"Blogs: {sent} new deal post(s) forwarded.")
    save_json(SEEN, seen)


if __name__ == "__main__":
    main()
