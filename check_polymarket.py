import requests
import json

EVENTS_URL = "https://gamma-api.polymarket.com/events"

params = {
    "limit": 100,
    "active": "true",
    "closed": "false",
    "tag_slug": "nfl",
}

response = requests.get(EVENTS_URL, params=params, timeout=30)
response.raise_for_status()

events = response.json()

print(f"Found {len(events)} active NFL events.\n")

for event in events:
    print("=" * 70)
    print("EVENT:", event.get("title"))
    print("SLUG:", event.get("slug"))

    markets = event.get("markets", [])

    print(f"MARKETS: {len(markets)}")

    for market in markets:
        print("\n  QUESTION:", market.get("question"))

        outcomes = market.get("outcomes")
        prices = market.get("outcomePrices")

        # Polymarket sometimes returns these as JSON strings
        try:
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)

            if isinstance(prices, str):
                prices = json.loads(prices)
        except json.JSONDecodeError:
            pass

        print("  OUTCOMES:", outcomes)
        print("  PRICES:", prices)
        print("  ACTIVE:", market.get("active"))
        print("  CLOSED:", market.get("closed"))

print("\n" + "=" * 70)
print("Polymarket NFL connection successful.")
