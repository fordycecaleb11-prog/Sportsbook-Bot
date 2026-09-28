import requests

URL = "https://gamma-api.polymarket.com/events"

params = {
    "limit": 500,
    "active": "true",
    "closed": "false",
    "tag_slug": "nfl",
}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

events = response.json()

print(f"Pulled {len(events)} NFL-tagged events.\n")

possible_games = []

for event in events:
    title = event.get("title", "")
    lower = title.lower()

    if (
        " vs " in lower
        or " vs. " in lower
        or " @ " in lower
        or " versus " in lower
    ):
        possible_games.append(event)

print(f"Found {len(possible_games)} matchup-looking events.\n")

for event in possible_games:
    print("=" * 70)
    print("TITLE:", event.get("title"))
    print("SLUG:", event.get("slug"))
    print("END DATE:", event.get("endDate"))

    for market in event.get("markets", []):
        print("  QUESTION:", market.get("question"))
        print("  OUTCOMES:", market.get("outcomes"))
        print("  PRICES:", market.get("outcomePrices"))
        print("  CLOSED:", market.get("closed"))

print("\nDiagnostic complete.")
