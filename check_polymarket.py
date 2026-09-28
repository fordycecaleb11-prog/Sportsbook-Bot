import requests
import json

URL = "https://gamma-api.polymarket.com/events"

params = {
    "series_id": 12185,
    "active": "true",
    "closed": "false",
    "limit": 100,
}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

events = response.json()

print(f"Found {len(events)} NFL series events.\n")

moneyline_count = 0

for event in events:

    moneyline_markets = []

    for market in event.get("markets", []):

        market_type = market.get("sportsMarketType")

        if market_type != "moneyline":
            continue

        if market.get("closed") is True:
            continue

        outcomes = market.get("outcomes")
        prices = market.get("outcomePrices")

        try:
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)

            if isinstance(prices, str):
                prices = json.loads(prices)

        except (json.JSONDecodeError, TypeError):
            continue

        moneyline_markets.append({
            "question": market.get("question"),
            "outcomes": outcomes,
            "prices": prices,
            "type": market_type,
            "start": market.get("gameStartTime"),
        })

    if not moneyline_markets:
        continue

    print("=" * 70)
    print("EVENT:", event.get("title"))
    print("SLUG:", event.get("slug"))
    print("START:", event.get("startDate"))
    print("END:", event.get("endDate"))

    for market in moneyline_markets:

        moneyline_count += 1

        print()
        print("  TYPE:", market["type"])
        print("  QUESTION:", market["question"])
        print("  OUTCOMES:", market["outcomes"])
        print("  PRICES:", market["prices"])
        print("  GAME START:", market["start"])

print("\n" + "=" * 70)
print(f"Found {moneyline_count} active NFL moneyline markets.")
print("Diagnostic complete.")
