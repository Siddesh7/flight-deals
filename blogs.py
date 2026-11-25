#!/usr/bin/env python3
"""Forward hand-picked deals from US deal blogs to Telegram.

Polls WordPress deal blogs (escape.flights and its sister sites, The Flight Deal)
and RSS feeds (Fly4free) for new posts and
forwards only the ones that touch India (as origin or destination). A US-Europe
deal is no use when you start from Chennai.
"""

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from deals import CONFIG, HERE, load_json, save_json, send_telegram

SEEN = HERE / "data" / "blog_seen.json"


def keywords(config):
    return {w.lower() for w in config["blogs"]["india_keywords"]}


def matches(title, words):
    """True if the title names an Indian city anywhere ('Delhi to Paris' or 'Paris to Delhi')."""
    title = title.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", title) for w in words)


def get(url):
    """Fetch a URL with a browser-ish User-Agent (some sites 403 Python's). None on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 flight-deals"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"{url} failed: {e}")
        return None


def fetch_posts(site):
    """Newest-first posts from a WordPress site, as {id, posted, title, link}."""
    query = urllib.parse.urlencode({"per_page": 50, "_fields": "id,date_gmt,title,link"})
    body = get(f"https://{site}/wp-json/wp/v2/posts?{query}")
    try:
        posts = json.loads(body) if body else []
    except json.JSONDecodeError:
        print(f"{site} returned non-JSON")
        posts = []
    return [{
        "id": p["id"],
        "posted": datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc),
        "title": html.unescape(p["title"]["rendered"]),
        "link": p["link"],
    } for p in posts]


def parse_rss(xml_text):
    """Newest-first items from an RSS feed, as {id, posted, title, link}."""
    posts = []
    for item in ET.fromstring(xml_text).iter("item"):
        link = item.findtext("link") or ""
        posts.append({
            "id": item.findtext("guid") or link,
            "posted": parsedate_to_datetime(item.findtext("pubDate")).astimezone(timezone.utc),
            "title": html.unescape(item.findtext("title") or ""),
            "link": link,
        })
    return posts


def fetch_feed(url):
    body = get(url)
    try:
        return parse_rss(body) if body else []
    except ET.ParseError as e:
        print(f"Feed {url} is not valid RSS: {e}")
        return []


def main():
    config = load_json(CONFIG, None)
    blogs = config["blogs"]
    words = keywords(config)
    seen = load_json(SEEN, {})
    cutoff = datetime.now(timezone.utc) - timedelta(hours=blogs["max_age_hours"])

    sources = [(site, site, lambda s=site: fetch_posts(s)) for site in blogs["sites"]]
    sources += [(url, urllib.parse.urlparse(url).netloc, lambda u=url: fetch_feed(u))
                for url in blogs.get("rss_feeds", [])]

    sent = 0
    for key, label, fetch in sources:
        site_seen = set(seen.get(key, []))
        posts = fetch()
        for post in reversed(posts):  # oldest first
            if post["id"] in site_seen:
                continue
            site_seen.add(post["id"])
            if post["posted"] < cutoff or not matches(post["title"], words):
                continue
            send_telegram(f"📰 <b>{html.escape(post['title'])}</b>\n"
                          f'<a href="{post["link"]}">Read on {label}</a>')
            sent += 1
        # Keep only ids the site still lists, so the file doesn't grow forever.
        listed = {p["id"] for p in posts}
        seen[key] = sorted(site_seen & listed) if listed else sorted(site_seen)

    print(f"Blogs: {sent} new deal post(s) forwarded.")
    save_json(SEEN, seen)


if __name__ == "__main__":
    main()
