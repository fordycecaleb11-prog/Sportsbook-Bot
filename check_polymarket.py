import requests

URL = "https://gamma-api.polymarket.com/events"

params = {
    "limit": 1000,
    "active": "true",
    "closed": "false",
}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

events = response.json()

print(f"Pulled {len(events)} active events.\n")

search_terms = ["Eagles", "Bears"]

matches = []

for event in events:
    title = event.get("title", "")
    slug = event.get("slug", "")

    combined = f"{title} {slug}".lower()

    # Require BOTH teams
    if all(term.lower() in combined for term in search_terms):
        matches.append(event)

print(f"Found {len(matches)} Eagles/Bears events.\n")

for event in matches:
    print("=" * 70)
    print("TITLE:", event.get("title"))
    print("SLUG:", event.get("slug"))
    print("START:", event.get("startDate"))
    print("END:", event.get("endDate"))

    for market in event.get("markets", []):
        print()
        print("  QUESTION:", market.get("question"))
        print("  OUTCOMES:", market.get("outcomes"))
        print("  PRICES:", market.get("outcomePrices"))
        print("  ACTIVE:", market.get("active"))
        print("  CLOSED:", market.get("closed"))

print("\nDiagnostic complete.")
