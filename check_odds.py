import os
import requests

API_KEY = os.environ.get("ODDS_API_KEY")

if not API_KEY:
    raise RuntimeError("ODDS_API_KEY is missing.")

url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"

params = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "h2h",
    "oddsFormat": "american",
}

response = requests.get(url, params=params, timeout=20)
response.raise_for_status()

games = response.json()

print(f"Found {len(games)} NFL games.\n")

for game in games:
    away = game["away_team"]
    home = game["home_team"]

    print(f"{away} @ {home}")

    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] != "h2h":
                continue

            prices = {
                outcome["name"]: outcome["price"]
                for outcome in market["outcomes"]
            }

            print(
                f"  {bookmaker['title']}: "
                f"{away} {prices.get(away)} | "
                f"{home} {prices.get(home)}"
            )

    print("-" * 60)

print("Sportsbook connection successful.")
