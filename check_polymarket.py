import requests
import json

SPORTS_URL = "https://gamma-api.polymarket.com/sports"
MARKET_TYPES_URL = "https://gamma-api.polymarket.com/sports/market-types"

print("Fetching Polymarket sports metadata...\n")

sports_response = requests.get(SPORTS_URL, timeout=30)
sports_response.raise_for_status()

sports = sports_response.json()

print(f"Found {len(sports)} sports.\n")

# Find anything that appears to be NFL / American football
nfl_results = []

for sport in sports:
    text = json.dumps(sport).lower()

    if "nfl" in text:
        nfl_results.append(sport)

print(f"Found {len(nfl_results)} NFL metadata entries.\n")

for sport in nfl_results:
    print("=" * 70)
    print(json.dumps(sport, indent=2))


print("\nFetching valid sports market types...\n")

types_response = requests.get(MARKET_TYPES_URL, timeout=30)
types_response.raise_for_status()

market_types = types_response.json()

print(json.dumps(market_types, indent=2))

print("\nDiagnostic complete.")
