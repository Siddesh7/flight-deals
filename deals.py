#!/usr/bin/env python3
"""Cheap flight deal finder.

Pulls cached fares from the Travelpayouts (Aviasales) Data API for every
India <-> destination pair in config.json, compares each fare against the
route's usual price and a per-region "no-brainer" price, and pings Telegram
when something is unusually cheap.

Env vars:
  TRAVELPAYOUTS_TOKEN   API token from travelpayouts.com (required)
  TELEGRAM_BOT_TOKEN    bot token from @BotFather (optional; prints if unset)
  TELEGRAM_CHAT_ID      your chat id (optional; prints if unset)
"""

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
CONFIG = HERE / "config.json"
HISTORY = HERE / "data" / "history.json"
ALERTED = HERE / "data" / "alerted.json"

API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def http_get_json(url, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            time.sleep(2 ** (attempt + 1))
    return None


def fetch_fares(token, origin, destination, one_way, currency):
    params = {
        "origin": origin,
        "destination": destination,
        "one_way": "true" if one_way else "false",
        "currency": currency,
        "sorting": "price",
        "limit": 30,
        "token": token,
    }
    data = http_get_json(f"{API}?{urllib.parse.urlencode(params)}")
    if not data or not data.get("success"):
        return []
    return data.get("data") or []


def searches(config):
    """Yield (route_key, region, trip_type, api_origin, api_dest, india_airport, dest_name)."""
    for region, spec in config["regions"].items():
        for dest, name in spec["destinations"].items():
            for trip in config["trip_types"]:
                if trip == "one_way_back":
                    for home in config["return_airports"]:
                        yield f"{dest}-{home}-{trip}", region, trip, dest, home, home, name
                else:
                    for home in config["origins"]:
                        yield f"{home}-{dest}-{trip}", region, trip, home, dest, home, name


def threshold(config, region, trip):
    return config["regions"][region][trip]


def evaluate(price, past_prices, abs_limit, config):
    """Return a list of reasons this price is a deal (empty if not)."""
    reasons = []
    if price <= abs_limit:
        reasons.append(f"under your ₹{abs_limit:,} no-brainer price")
    if len(past_prices) >= config["min_history"]:
        usual = statistics.median(past_prices)
        drop = 1 - price / usual
        if drop >= config["relative_drop"]:
            reasons.append(f"{drop:.0%} below usual (~₹{usual:,.0f})")
    return reasons


def fmt_date(iso):
    return iso[:10] if iso else ""


def format_alert(deal):
    t = deal["ticket"]
    trip_label = {
        "round_trip": "Round trip",
        "one_way_out": "One way",
        "one_way_back": "One way (back home)",
    }[deal["trip"]]
    dates = fmt_date(t.get("departure_at"))
    if t.get("return_at"):
        dates += f" → {fmt_date(t['return_at'])}"
    stops = t.get("transfers", 0)
    if t.get("return_transfers") is not None and deal["trip"] == "round_trip":
        stops = f"{stops} out / {t['return_transfers']} back"
    lines = [
        f"✈️ <b>{t['origin']} → {t['destination']}</b> · {deal['dest_name']}",
        f"{trip_label} · <b>₹{t['price']:,}</b> ({t.get('airline', '?')})",
        f"Dates: {dates}",
        f"Stops: {stops}",
    ]
    if deal["positioning"]:
        lines.append(f"+ ~₹{deal['positioning']:,} to get to/from {deal['home']} "
                     f"→ effective ₹{deal['effective']:,}")
    lines.append("Why: " + "; ".join(deal["reasons"]))
    if t.get("link"):
        lines.append(f'<a href="https://www.aviasales.com{t["link"]}">Book / check it</a>')
    lines.append("<i>Cached fare. Verify before booking.</i>")
    return "\n".join(lines)


def send_telegram(text):
    bot = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot or not chat:
        print(text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))
        print("-" * 40)
        return
    body = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{bot}/sendMessage", body, timeout=30)


def main():
    token = os.environ.get("TRAVELPAYOUTS_TOKEN")
    if not token:
        sys.exit("TRAVELPAYOUTS_TOKEN is not set")

    config = load_json(CONFIG, None)
    history = load_json(HISTORY, {})
    alerted = load_json(ALERTED, {})
    now = datetime.now(timezone.utc)
    realert_cutoff = now - timedelta(days=config["realert_after_days"])
    alerted = {k: v for k, v in alerted.items()
               if datetime.fromisoformat(v) > realert_cutoff}

    deals = []
    for key, region, trip, o, d, home, name in searches(config):
        tickets = fetch_fares(token, o, d, trip != "round_trip", config["currency"])
        tickets = [t for t in tickets
                   if t.get("transfers", 0) <= config["max_transfers"]
                   and (t.get("return_transfers") or 0) <= config["max_transfers"]]
        time.sleep(0.2)
        if not tickets:
            continue

        best = min(tickets, key=lambda t: t["price"])
        airports = config["return_airports"] if trip == "one_way_back" else config["origins"]
        positioning = airports[home]
        effective = best["price"] + positioning
        past = history.get(key, [])
        reasons = evaluate(effective, past, threshold(config, region, trip), config)
        history[key] = (past + [effective])[-config["history_keep"]:]

        if not reasons:
            continue
        # Same route, dates and roughly the same price -> don't spam.
        dedupe = f"{key}|{fmt_date(best.get('departure_at'))}|{fmt_date(best.get('return_at'))}|{effective // 1000}"
        if dedupe in alerted:
            continue
        alerted[dedupe] = now.isoformat()
        deals.append({
            "ticket": best, "trip": trip, "dest_name": name, "home": home,
            "positioning": positioning, "effective": effective, "reasons": reasons,
        })

    deals.sort(key=lambda x: x["effective"])
    for deal in deals:
        send_telegram(format_alert(deal))
    print(f"Checked {sum(1 for _ in searches(config))} searches, {len(deals)} new deal(s).")

    save_json(HISTORY, history)
    save_json(ALERTED, alerted)


if __name__ == "__main__":
    main()
