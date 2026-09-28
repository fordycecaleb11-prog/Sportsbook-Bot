import requests

URL = "https://gamma-api.polymarket.com/markets"

params = {
    "limit": 500,
    "active": "true",
    "closed": "false",
}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

markets = response.json()

print(f"Pulled {len(markets)} active Polymarket markets.\n")

# NFL team names/keywords to help identify relevant markets
nfl_keywords = [
    "Chiefs", "Raiders", "Broncos", "Chargers",
    "Bills", "Dolphins", "Patriots", "Jets",
    "Ravens", "Bengals", "Browns", "Steelers",
    "Texans", "Colts", "Jaguars", "Titans",
    "Eagles", "Cowboys", "Giants", "Commanders",
    "Packers", "Lions", "Vikings", "Bears",
    "Falcons", "Panthers", "Saints", "Buccaneers",
    "49ers", "Rams", "Seahawks", "Cardinals",
    "NFL",
]

found = []

for market in markets:
    question = market.get("question", "")

    if any(keyword.lower() in question.lower() for keyword in nfl_keywords):
        found.append(market)

print(f"Found {len(found)} possible NFL markets.\n")

for market in found:
    print("QUESTION:", market.get("question"))
    print("OUTCOMES:", market.get("outcomes"))
    print("PRICES:", market.get("outcomePrices"))
    print("END DATE:", market.get("endDate"))
    print("SLUG:", market.get("slug"))
    print("-" * 70)

print("\nPolymarket connection successful.")
