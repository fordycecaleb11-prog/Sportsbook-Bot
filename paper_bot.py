import os
import json
import requests
from datetime import datetime, timezone

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

if not ODDS_API_KEY:
    raise RuntimeError("ODDS_API_KEY is missing.")

POLY_URL = "https://gamma-api.polymarket.com/events"
ODDS_URL = (
    "https://api.the-odds-api.com/v4/"
    "sports/americanfootball_nfl/odds"
)

NFL_SERIES_ID = 12185
MIN_ARB_ROI = 0.01
PAPER_STAKE = 100.00

# Converts Polymarket short team names to sportsbook full names.
TEAM_MAP = {
    "49ers": "San Francisco 49ers",
    "Bears": "Chicago Bears",
    "Bengals": "Cincinnati Bengals",
    "Bills": "Buffalo Bills",
    "Broncos": "Denver Broncos",
    "Browns": "Cleveland Browns",
    "Buccaneers": "Tampa Bay Buccaneers",
    "Cardinals": "Arizona Cardinals",
    "Chargers": "Los Angeles Chargers",
    "Chiefs": "Kansas City Chiefs",
    "Colts": "Indianapolis Colts",
    "Commanders": "Washington Commanders",
    "Cowboys": "Dallas Cowboys",
    "Dolphins": "Miami Dolphins",
    "Eagles": "Philadelphia Eagles",
    "Falcons": "Atlanta Falcons",
    "Giants": "New York Giants",
    "Jaguars": "Jacksonville Jaguars",
    "Jets": "New York Jets",
    "Lions": "Detroit Lions",
    "Packers": "Green Bay Packers",
    "Panthers": "Carolina Panthers",
    "Patriots": "New England Patriots",
    "Raiders": "Las Vegas Raiders",
    "Rams": "Los Angeles Rams",
    "Ravens": "Baltimore Ravens",
    "Saints": "New Orleans Saints",
    "Seahawks": "Seattle Seahawks",
    "Steelers": "Pittsburgh Steelers",
    "Texans": "Houston Texans",
    "Titans": "Tennessee Titans",
    "Vikings": "Minnesota Vikings",
}


def american_decimal(odds):
    if odds > 0:
        return 1 + (odds / 100)

    return 1 + (100 / abs(odds))


def parse_time(value):
    if not value:
        return None

    value = str(value).replace(" ", "T").replace("+00", "+00:00")

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except ValueError:
        return None


def get_polymarket_games():
    params = {
        "series_id": NFL_SERIES_ID,
        "active": "true",
        "closed": "false",
        "limit": 100,
    }

    r = requests.get(POLY_URL, params=params, timeout=30)
    r.raise_for_status()

    games = []

    for event in r.json():

        for market in event.get("markets", []):

            if market.get("sportsMarketType") != "moneyline":
                continue

            if market.get("closed") is True:
                continue

            try:
                outcomes = market.get("outcomes")
                prices = market.get("outcomePrices")

                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)

                if isinstance(prices, str):
                    prices = json.loads(prices)

                if len(outcomes) != 2 or len(prices) != 2:
                    continue

                full_teams = [
                    TEAM_MAP.get(outcomes[0]),
                    TEAM_MAP.get(outcomes[1]),
                ]

                if None in full_teams:
                    continue

                prices = [float(prices[0]), float(prices[1])]

                # Reject malformed prices.
                if any(p <= 0 or p >= 1 for p in prices):
                    continue

                games.append({
                    "title": event.get("title"),
                    "teams": full_teams,
                    "short_teams": outcomes,
                    "prices": prices,
                    "start": parse_time(
                        market.get("gameStartTime")
                        or event.get("endDate")
                    ),
                })

            except (ValueError, TypeError, json.JSONDecodeError):
                continue

    return games


def get_sportsbook_games():

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
    }

    r = requests.get(ODDS_URL, params=params, timeout=30)
    r.raise_for_status()

    return r.json()


def same_game(poly, book):

    poly_teams = set(poly["teams"])

    book_teams = {
        book.get("home_team"),
        book.get("away_team"),
    }

    if poly_teams != book_teams:
        return False

    poly_time = poly["start"]
    book_time = parse_time(book.get("commence_time"))

    if poly_time and book_time:
        difference = abs(
            (poly_time - book_time).total_seconds()
        )

        # Allow up to 3 hours in case one feed has
        # scheduling/time discrepancies.
        if difference > 10800:
            return False

    return True


def calculate_arb(poly_price, american_odds):

    sportsbook_decimal = american_decimal(american_odds)

    # $1 Polymarket share costs poly_price and pays $1.
    #
    # For equal payout:
    # sportsbook_stake * decimal_odds = polymarket_shares
    #
    # Solve for total cost needed to guarantee $1 payout.

    cost_per_guaranteed_dollar = (
        poly_price + (1 / sportsbook_decimal)
    )

    if cost_per_guaranteed_dollar >= 1:
        return None

    guaranteed_payout = (
        PAPER_STAKE / cost_per_guaranteed_dollar
    )

    poly_stake = poly_price * guaranteed_payout

    sportsbook_stake = (
        guaranteed_payout / sportsbook_decimal
    )

    profit = guaranteed_payout - PAPER_STAKE
    roi = profit / PAPER_STAKE

    return {
        "poly_stake": poly_stake,
        "sportsbook_stake": sportsbook_stake,
        "payout": guaranteed_payout,
        "profit": profit,
        "roi": roi,
    }


def main():

    print("POLYMARKET × SPORTSBOOK PAPER ARB SCANNER")
    print("=" * 70)

    poly_games = get_polymarket_games()
    book_games = get_sportsbook_games()

    print(f"Polymarket moneylines: {len(poly_games)}")
    print(f"Sportsbook games:      {len(book_games)}")
    print()

    matched_games = 0
    combinations = 0
    opportunities = []

    for poly in poly_games:

        for book in book_games:

            if not same_game(poly, book):
                continue

            matched_games += 1

            team_a = poly["teams"][0]
            team_b = poly["teams"][1]

            poly_a = poly["prices"][0]
            poly_b = poly["prices"][1]

            for bookmaker in book.get("bookmakers", []):

                for market in bookmaker.get("markets", []):

                    if market.get("key") != "h2h":
                        continue

                    odds = {
                        outcome["name"]: outcome["price"]
                        for outcome in market.get("outcomes", [])
                    }

                    if team_a not in odds or team_b not in odds:
                        continue

                    # Direction 1:
                    # Polymarket A + sportsbook B
                    combinations += 1

                    arb = calculate_arb(
                        poly_a,
                        odds[team_b],
                    )

                    if arb and arb["roi"] >= MIN_ARB_ROI:

                        opportunities.append({
                            "game": poly["title"],
                            "poly_team": team_a,
                            "poly_price": poly_a,
                            "book_team": team_b,
                            "book_odds": odds[team_b],
                            "book": bookmaker["title"],
                            **arb,
                        })

                    # Direction 2:
                    # Polymarket B + sportsbook A
                    combinations += 1

                    arb = calculate_arb(
                        poly_b,
                        odds[team_a],
                    )

                    if arb and arb["roi"] >= MIN_ARB_ROI:

                        opportunities.append({
                            "game": poly["title"],
                            "poly_team": team_b,
                            "poly_price": poly_b,
                            "book_team": team_a,
                            "book_odds": odds[team_a],
                            "book": bookmaker["title"],
                            **arb,
                        })

    opportunities.sort(
        key=lambda x: x["roi"],
        reverse=True,
    )

    print(f"Matched NFL games: {matched_games}")
    print(f"Combinations checked: {combinations}")
    print(
        f"Paper arbitrages >= {MIN_ARB_ROI * 100:.2f}%: "
        f"{len(opportunities)}"
    )

    print()

    if not opportunities:
        print("NO PAPER ARBITRAGES FOUND.")
        return

    print("PAPER ARBITRAGES FOUND")
    print("=" * 70)

    for x in opportunities:

        print()
        print(f"GAME: {x['game']}")
        print(
            f"Polymarket: {x['poly_team']} "
            f"@ ${x['poly_price']:.3f}"
        )

        print(
            f"{x['book']}: {x['book_team']} "
            f"@ {x['book_odds']:+d}"
        )

        print()
        print(f"Total paper stake: ${PAPER_STAKE:.2f}")

        print(
            f"  Polymarket stake: "
            f"${x['poly_stake']:.2f}"
        )

        print(
            f"  Sportsbook stake: "
            f"${x['sportsbook_stake']:.2f}"
        )

        print(
            f"Guaranteed payout: "
            f"${x['payout']:.2f}"
        )

        print(
            f"Paper profit: "
            f"${x['profit']:.2f}"
        )

        print(
            f"ROI: {x['roi'] * 100:.2f}%"
        )

        print("-" * 70)


if __name__ == "__main__":
    main()
