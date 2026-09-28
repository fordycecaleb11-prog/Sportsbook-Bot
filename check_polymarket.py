import requests
import json

EVENTS_URL = "https://gamma-api.polymarket.com/events"

NFL_TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens",
    "Buffalo Bills", "Carolina Panthers", "Chicago Bears",
    "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys",
    "Denver Broncos", "Detroit Lions", "Green Bay Packers",
    "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars",
    "Kansas City Chiefs", "Las Vegas Raiders", "Los Angeles Chargers",
    "Los Angeles Rams", "Miami Dolphins", "Minnesota Vikings",
    "New England Patriots", "New Orleans Saints", "New York Giants",
    "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers",
    "San Francisco 49ers", "Seattle Seahawks", "Tampa Bay Buccaneers",
    "Tennessee Titans", "Washington Commanders"
]

params = {
    "limit": 500,
    "active": "true",
    "closed": "false",
    "tag_slug": "nfl",
}

response = requests.get(EVENTS_URL, params=params, timeout=30)
response.raise_for_status()

events = response.json()

print(f"Pulled {len(events)} NFL-tagged events.\n")

game_events = []

for event in events:
    title = event.get("title", "")

    # Find NFL teams appearing in the event title
    teams_found = [
        team for team in NFL_TEAMS
        if team.lower() in title.lower()
    ]

    # A weekly matchup should contain two NFL teams
    if len(teams_found) != 2:
        continue

    markets = []

    for market in event.get("markets", []):
        if market.get("closed") is True:
            continue

        if market.get("active") is False:
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

        markets.append({
            "question": market.get("question"),
            "outcomes": outcomes,
            "prices": prices,
        })

    if markets:
        game_events.append({
            "title": title,
            "teams": teams_found,
            "markets": markets,
        })


print(f"Found {len(game_events)} possible NFL GAME events.\n")

for event in game_events:

    print("=" * 70)
    print("GAME:", event["title"])
    print("TEAMS:", event["teams"])

    for market in event["markets"]:
        print("\n  QUESTION:", market["question"])
        print("  OUTCOMES:", market["outcomes"])
        print("  PRICES:", market["prices"])

print("\n" + "=" * 70)
print("NFL game filtering complete.")
