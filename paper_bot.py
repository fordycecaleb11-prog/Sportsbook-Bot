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
TOP_RESULTS = 10

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
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

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

    response = requests.get(
        POLY_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    games = []

    print()
    print("POLYMARKET CLOB TOKEN DIAGNOSTIC")
    print("=" * 70)

    diagnostic_count = 0

    for event in response.json():

        for market in event.get("markets", []):

            if market.get("sportsMarketType") != "moneyline":
                continue

            if market.get("closed") is True:
                continue

            try:
                outcomes = market.get("outcomes")
                prices = market.get("outcomePrices")
                token_ids = market.get("clobTokenIds")

                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)

                if isinstance(prices, str):
                    prices = json.loads(prices)

                if isinstance(token_ids, str):
                    token_ids = json.loads(token_ids)

                if len(outcomes) != 2:
                    continue

                if len(prices) != 2:
                    continue

                # Print only the first 3 moneyline markets
                # so the GitHub output doesn't get flooded.
                if diagnostic_count < 3:

                    print()
                    print(
                        "GAME:",
                        event.get("title")
                    )

                    print(
                        "OUTCOMES:",
                        outcomes
                    )

                    print(
                        "DISPLAY PRICES:",
                        prices
                    )

                    print(
                        "CLOB TOKEN IDS:",
                        token_ids
                    )

                    diagnostic_count += 1

                team_a = TEAM_MAP.get(outcomes[0])
                team_b = TEAM_MAP.get(outcomes[1])

                if not team_a or not team_b:
                    continue

                price_a = float(prices[0])
                price_b = float(prices[1])

                if not 0 < price_a < 1:
                    continue

                if not 0 < price_b < 1:
                    continue

                games.append({
                    "title": event.get("title"),
                    "teams": [
                        team_a,
                        team_b,
                    ],
                    "short_teams": outcomes,
                    "prices": [
                        price_a,
                        price_b,
                    ],
                    "token_ids": token_ids,
                    "start": parse_time(
                        market.get("gameStartTime")
                        or event.get("endDate")
                    ),
                })

            except (
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ):
                continue

    print()
    print("=" * 70)

    return games


def get_sportsbook_games():

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
    }

    response = requests.get(
        ODDS_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def same_game(poly, book):

    poly_teams = set(poly["teams"])

    book_teams = {
        book.get("home_team"),
        book.get("away_team"),
    }

    if poly_teams != book_teams:
        return False

    poly_time = poly["start"]
    book_time = parse_time(
        book.get("commence_time")
    )

    if poly_time and book_time:

        difference = abs(
            (poly_time - book_time).total_seconds()
        )

        if difference > 10800:
            return False

    return True


def calculate_comparison(poly_price, american_odds):

    decimal_odds = american_decimal(
        american_odds
    )

    cost_per_dollar = (
        poly_price
        + (1 / decimal_odds)
    )

    guaranteed_payout = (
        PAPER_STAKE
        / cost_per_dollar
    )

    poly_stake = (
        poly_price
        * guaranteed_payout
    )

    sportsbook_stake = (
        guaranteed_payout
        / decimal_odds
    )

    profit = (
        guaranteed_payout
        - PAPER_STAKE
    )

    roi = (
        profit
        / PAPER_STAKE
    )

    return {
        "poly_stake": poly_stake,
        "sportsbook_stake": sportsbook_stake,
        "payout": guaranteed_payout,
        "profit": profit,
        "roi": roi,
    }


def make_comparison(
    poly,
    poly_team,
    poly_price,
    book_team,
    book_odds,
    bookmaker,
):

    result = calculate_comparison(
        poly_price,
        book_odds,
    )

    return {
        "game": poly["title"],
        "poly_team": poly_team,
        "poly_price": poly_price,
        "book_team": book_team,
        "book_odds": book_odds,
        "book": bookmaker,
        **result,
    }


def main():

    print(
        "POLYMARKET × SPORTSBOOK "
        "PAPER ARB SCANNER"
    )

    print("=" * 70)

    poly_games = get_polymarket_games()
    book_games = get_sportsbook_games()

    print()
    print(
        f"Polymarket moneylines: "
        f"{len(poly_games)}"
    )

    print(
        f"Sportsbook games:      "
        f"{len(book_games)}"
    )

    print()

    matched_games = 0
    combinations = 0

    all_comparisons = []
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

            for bookmaker in book.get(
                "bookmakers",
                [],
            ):

                for market in bookmaker.get(
                    "markets",
                    [],
                ):

                    if market.get("key") != "h2h":
                        continue

                    odds = {
                        outcome["name"]:
                        outcome["price"]

                        for outcome
                        in market.get(
                            "outcomes",
                            [],
                        )
                    }

                    if team_a not in odds:
                        continue

                    if team_b not in odds:
                        continue

                    book_name = bookmaker.get(
                        "title",
                        "Unknown",
                    )

                    # Direction 1
                    combinations += 1

                    comparison = make_comparison(
                        poly,
                        team_a,
                        poly_a,
                        team_b,
                        odds[team_b],
                        book_name,
                    )

                    all_comparisons.append(
                        comparison
                    )

                    if (
                        comparison["roi"]
                        >= MIN_ARB_ROI
                    ):
                        opportunities.append(
                            comparison
                        )

                    # Direction 2
                    combinations += 1

                    comparison = make_comparison(
                        poly,
                        team_b,
                        poly_b,
                        team_a,
                        odds[team_a],
                        book_name,
                    )

                    all_comparisons.append(
                        comparison
                    )

                    if (
                        comparison["roi"]
                        >= MIN_ARB_ROI
                    ):
                        opportunities.append(
                            comparison
                        )

    all_comparisons.sort(
        key=lambda x: x["roi"],
        reverse=True,
    )

    opportunities.sort(
        key=lambda x: x["roi"],
        reverse=True,
    )

    print(
        f"Matched NFL games: "
        f"{matched_games}"
    )

    print(
        f"Combinations checked: "
        f"{combinations}"
    )

    print(
        f"Paper arbitrages >= "
        f"{MIN_ARB_ROI * 100:.2f}%: "
        f"{len(opportunities)}"
    )

    print()

    print(
        f"TOP {TOP_RESULTS} "
        "CROSS-MARKET COMPARISONS"
    )

    print("=" * 70)

    for i, x in enumerate(
        all_comparisons[:TOP_RESULTS],
        start=1,
    ):

        print()

        print(
            f"{i}. {x['game']}"
        )

        print(
            f"   Polymarket "
            f"{x['poly_team']}: "
            f"${x['poly_price']:.3f}"
        )

        print(
            f"   {x['book']} "
            f"{x['book_team']}: "
            f"{x['book_odds']:+d}"
        )

        print(
            f"   Theoretical ROI: "
            f"{x['roi'] * 100:+.2f}%"
        )

    print()
    print("=" * 70)

    if not opportunities:

        print(
            "NO PAPER ARBITRAGES "
            f">= {MIN_ARB_ROI * 100:.2f}% FOUND."
        )

        return

    print("PAPER ARBITRAGES FOUND")
    print("=" * 70)

    for x in opportunities:

        print()
        print(f"GAME: {x['game']}")

        print(
            f"Polymarket: "
            f"{x['poly_team']} "
            f"@ ${x['poly_price']:.3f}"
        )

        print(
            f"{x['book']}: "
            f"{x['book_team']} "
            f"@ {x['book_odds']:+d}"
        )

        print(
            f"Total paper stake: "
            f"${PAPER_STAKE:.2f}"
        )

        print(
            f"Polymarket stake: "
            f"${x['poly_stake']:.2f}"
        )

        print(
            f"Sportsbook stake: "
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
            f"ROI: "
            f"{x['roi'] * 100:.2f}%"
        )

        print("-" * 70)


if __name__ == "__main__":
    main()
