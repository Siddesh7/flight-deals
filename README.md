# Flight deal finder

Pings you on Telegram when a flight from Chennai, Bangalore or Delhi to Europe, the US
or other easy-visa countries is unusually cheap.

## How it works
- Every 3 hours, `.github/workflows/flight-deals.yml` runs `deals.py` and `blogs.py`.
- For each destination in `config.json`, it pulls the cheapest cached fares from the
  Travelpayouts (Aviasales) API for:
  - round trip and one way out, from MAA, BLR or DEL
  - **one way back home**, from that European/US city to MAA, BLR, DEL, BOM or HYD. This is
    usually the expensive leg, so it's the one most worth catching.
- A fare is a deal if either:
  - it's under the region's **no-brainer price** for that trip type (e.g. Europe round
    trip ≤ ₹38,000, Europe → India one way ≤ ₹20,000), or
  - it's **45%+ below that route's usual price**, once ~2 days of history exist.
  Small dips never alert.
- The cost of getting to or from Chennai (bus to BLR, domestic flight from DEL/BOM/HYD) is
  added first, so other airports only win when they're still cheaper after that.
- The same deal won't alert again for 3 days. Price history lives in `data/` and is
  committed back by the workflow.

### Deal blogs (`blogs.py`)
Also forwards new posts from US deal blogs (escape.flights, escapehouston.com,
cheapdfw.com, escapeatx.com). Only posts whose title mentions an Indian city (as origin
or destination) are sent; US-Europe, US-Asia and US domestic deals are skipped. Change
`india_keywords` under `blogs` in `config.json`.

## Setup (one time)
1. **Travelpayouts token**: sign up at travelpayouts.com → Profile → API token.
2. **Telegram bot**: message @BotFather → `/newbot` → copy the token. Send your bot any
   message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy
   `chat.id`.
3. In GitHub → repo Settings → Secrets and variables → Actions, add
   `TRAVELPAYOUTS_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
4. Scheduled runs only fire from the default branch, so merge this there. Then trigger
   it once by hand from the Actions tab.

## Tweaking
Everything is in `config.json`: outbound and return airports with their positioning cost, regions, destinations,
no-brainer prices, the % drop, and max stops.

## Run locally
```bash
TRAVELPAYOUTS_TOKEN=... python3 deals.py   # prints deals if Telegram isn't set
python3 -m unittest
python3 blogs.py                             # blog deals, no token needed
```

## Caveats
- Fares are **cached** from recent Aviasales searches, so some may be gone or changed.
  Always click through and check.
- Visa notes in `config.json` are a starting point. Entry rules change, so check before
  you book.
