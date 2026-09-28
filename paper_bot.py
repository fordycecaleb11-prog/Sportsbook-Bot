import os
import json
import requests
from datetime import datetime, timezone

ODDS_API_KEY = os.environ.get("ODDS_API_KEY")

if not ODDS_API_KEY:
    raise RuntimeError("ODDS_API_KEY is missing.")

POLY_URL = "https://gamma-api.polymarket.com/events"
CLOB_BOOK_URL = "https://clob.polymarket.com/book"

ODDS_URL = (
    "https://api.the-odds-api.com/v4/"
    "sports/americanfootball_nfl/odds"
)

NFL_SERIES_ID = 12185

PAPER_STAKE = 100.00
MIN_ARB_ROI = 0.01
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

    value = str(value).replace(" ", "T")

    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except ValueError:
        return None


# --------------------------------------------------
# POLYMARKET ORDER BOOK
# --------------------------------------------------

def get_order_book(token_id):
    try:
        response = requests.get(
            CLOB_BOOK_URL,
            params={"token_id": token_id},
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if not asks:
            return None

        # IMPORTANT:
        # Polymarket's response is not guaranteed to put
        # the best ask first.
        best_ask_entry = min(
            asks,
            key=lambda x: float(x["price"]),
        )

        best_ask = float(
            best_ask_entry["price"]
        )

        ask_size = float(
            best_ask_entry["size"]
        )

        best_bid = None
        bid_size = None

        if bids:

            best_bid_entry = max(
                bids,
                key=lambda x: float(x["price"]),
            )

            best_bid = float(
                best_bid_entry["price"]
            )

            bid_size = float(
                best_bid_entry["size"]
            )

        return {
            "best_ask": best_ask,
            "ask_size": ask_size,
            "best_bid": best_bid,
            "bid_size": bid_size,
            "last_trade": data.get(
                "last_trade_price"
            ),
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        KeyError,
    ):
        return None


# --------------------------------------------------
# POLYMARKET GAMES
# --------------------------------------------------

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

    for event in response.json():

        for market in event.get("markets", []):

            if (
                market.get("sportsMarketType")
                != "moneyline"
            ):
                continue

            if market.get("closed") is True:
                continue

            try:
                outcomes = market.get("outcomes")
                prices = market.get(
                    "outcomePrices"
                )
                tokens = market.get(
                    "clobTokenIds"
                )

                if isinstance(outcomes, str):
                    outcomes = json.loads(
                        outcomes
                    )

                if isinstance(prices, str):
                    prices = json.loads(
                        prices
                    )

                if isinstance(tokens, str):
                    tokens = json.loads(
                        tokens
                    )

                if len(outcomes) != 2:
                    continue

                if len(prices) != 2:
                    continue

                if not tokens or len(tokens) != 2:
                    continue

                team_a = TEAM_MAP.get(
                    outcomes[0]
                )

                team_b = TEAM_MAP.get(
                    outcomes[1]
                )

                if not team_a or not team_b:
                    continue

                display_a = float(prices[0])
                display_b = float(prices[1])

                games.append({
                    "title": event.get("title"),

                    "teams": [
                        team_a,
                        team_b,
                    ],

                    "display_prices": [
                        display_a,
                        display_b,
                    ],

                    "tokens": [
                        tokens[0],
                        tokens[1],
                    ],

                    "start": parse_time(
                        market.get(
                            "gameStartTime"
                        )
                        or event.get(
                            "endDate"
                        )
                    ),
                })

            except (
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ):
                continue

    return games


# --------------------------------------------------
# SPORTSBOOK DATA
# --------------------------------------------------

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

    if set(poly["teams"]) != {
        book.get("home_team"),
        book.get("away_team"),
    }:
        return False

    poly_time = poly["start"]

    book_time = parse_time(
        book.get("commence_time")
    )

    if poly_time and book_time:

        difference = abs(
            (
                poly_time
                - book_time
            ).total_seconds()
        )

        if difference > 10800:
            return False

    return True


# --------------------------------------------------
# ARBITRAGE MATH
# --------------------------------------------------

def calculate_comparison(
    poly_price,
    sportsbook_odds,
):

    decimal_odds = american_decimal(
        sportsbook_odds
    )

    cost_per_dollar = (
        poly_price
        + (1 / decimal_odds)
    )

    payout = (
        PAPER_STAKE
        / cost_per_dollar
    )

    poly_stake = (
        poly_price
        * payout
    )

    sportsbook_stake = (
        payout
        / decimal_odds
    )

    profit = (
        payout
        - PAPER_STAKE
    )

    roi = (
        profit
        / PAPER_STAKE
    )

    return {
        "poly_stake": poly_stake,
        "sportsbook_stake":
            sportsbook_stake,
        "payout": payout,
        "profit": profit,
        "roi": roi,
    }


def main():

    print(
        "POLYMARKET × SPORTSBOOK "
        "PAPER ARB SCANNER V3"
    )

    print("=" * 70)

    poly_games = get_polymarket_games()
    sportsbook_games = (
        get_sportsbook_games()
    )

    print(
        f"Polymarket moneylines: "
        f"{len(poly_games)}"
    )

    print(
        f"Sportsbook games:      "
        f"{len(sportsbook_games)}"
    )

    print()

    # Only request order books for teams
    # belonging to games that actually match
    # the sportsbook feed.
    matched_pairs = []

    for poly in poly_games:

        for book in sportsbook_games:

            if same_game(poly, book):

                matched_pairs.append(
                    (poly, book)
                )

                break

    print(
        f"Matched NFL games: "
        f"{len(matched_pairs)}"
    )

    print()
    print(
        "Fetching executable "
        "Polymarket prices..."
    )

    # Cache each token so we don't repeatedly
    # request the same order book.
    book_cache = {}

    for poly, _ in matched_pairs:

        for token in poly["tokens"]:

            if token not in book_cache:

                book_cache[token] = (
                    get_order_book(token)
                )

    valid_books = sum(
        1
        for value in book_cache.values()
        if value is not None
    )

    print(
        f"Valid CLOB books: "
        f"{valid_books}/"
        f"{len(book_cache)}"
    )

    print()

    comparisons = []

    for poly, sportsbook_game in matched_pairs:

        team_a = poly["teams"][0]
        team_b = poly["teams"][1]

        token_a = poly["tokens"][0]
        token_b = poly["tokens"][1]

        order_a = book_cache.get(
            token_a
        )

        order_b = book_cache.get(
            token_b
        )

        if not order_a or not order_b:
            continue

        ask_a = order_a["best_ask"]
        ask_b = order_b["best_ask"]

        display_a = (
            poly["display_prices"][0]
        )

        display_b = (
            poly["display_prices"][1]
        )

        for bookmaker in sportsbook_game.get(
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
                    x["name"]: x["price"]
                    for x in market.get(
                        "outcomes",
                        [],
                    )
                }

                if (
                    team_a not in odds
                    or team_b not in odds
                ):
                    continue

                book_name = bookmaker.get(
                    "title",
                    "Unknown",
                )

                # --------------------------
                # POLY A + SPORTSBOOK B
                # --------------------------

                result = (
                    calculate_comparison(
                        ask_a,
                        odds[team_b],
                    )
                )

                # Shares required at this
                # theoretical $100 allocation.
                required_shares = (
                    result["payout"]
                )

                available_shares = (
                    order_a["ask_size"]
                )

                enough_liquidity = (
                    available_shares
                    >= required_shares
                )

                comparisons.append({
                    "game":
                        poly["title"],

                    "poly_team":
                        team_a,

                    "display_price":
                        display_a,

                    "ask":
                        ask_a,

                    "ask_size":
                        available_shares,

                    "enough_liquidity":
                        enough_liquidity,

                    "book":
                        book_name,

                    "book_team":
                        team_b,

                    "book_odds":
                        odds[team_b],

                    **result,
                })

                # --------------------------
                # POLY B + SPORTSBOOK A
                # --------------------------

                result = (
                    calculate_comparison(
                        ask_b,
                        odds[team_a],
                    )
                )

                required_shares = (
                    result["payout"]
                )

                available_shares = (
                    order_b["ask_size"]
                )

                enough_liquidity = (
                    available_shares
                    >= required_shares
                )

                comparisons.append({
                    "game":
                        poly["title"],

                    "poly_team":
                        team_b,

                    "display_price":
                        display_b,

                    "ask":
                        ask_b,

                    "ask_size":
                        available_shares,

                    "enough_liquidity":
                        enough_liquidity,

                    "book":
                        book_name,

                    "book_team":
                        team_a,

                    "book_odds":
                        odds[team_a],

                    **result,
                })

    comparisons.sort(
        key=lambda x: x["roi"],
        reverse=True,
    )

    executable_arbs = [
        x
        for x in comparisons
        if (
            x["roi"] >= MIN_ARB_ROI
            and x["enough_liquidity"]
        )
    ]

    print(
        f"Comparisons checked: "
        f"{len(comparisons)}"
    )

    print(
        f"Executable paper arbs "
        f">= {MIN_ARB_ROI * 100:.2f}%: "
        f"{len(executable_arbs)}"
    )

    print()

    print(
        f"TOP {TOP_RESULTS} "
        "EXECUTABLE-PRICE COMPARISONS"
    )

    print("=" * 70)

    for i, x in enumerate(
        comparisons[:TOP_RESULTS],
        start=1,
    ):

        print()

        print(
            f"{i}. {x['game']}"
        )

        print(
            f"   Polymarket "
            f"{x['poly_team']}"
        )

        print(
            f"   Display: "
            f"${x['display_price']:.3f}"
        )

        print(
            f"   Best ask: "
            f"${x['ask']:.3f}"
        )

        print(
            f"   Ask liquidity: "
            f"{x['ask_size']:.2f} shares"
        )

        print(
            f"   {x['book']} "
            f"{x['book_team']}: "
            f"{x['book_odds']:+d}"
        )

        print(
            f"   Executable ROI: "
            f"{x['roi'] * 100:+.2f}%"
        )

        print(
            "   $100 liquidity: "
            + (
                "YES"
                if x["enough_liquidity"]
                else "NO"
            )
        )

    print()
    print("=" * 70)

    if not executable_arbs:

        print(
            "NO EXECUTABLE PAPER ARBS "
            f">= "
            f"{MIN_ARB_ROI * 100:.2f}%."
        )

        return

    print(
        "EXECUTABLE PAPER ARBS FOUND"
    )

    print("=" * 70)

    for x in executable_arbs:

        print()

        print(
            f"GAME: {x['game']}"
        )

        print(
            f"BUY POLYMARKET: "
            f"{x['poly_team']} "
            f"@ ${x['ask']:.3f}"
        )

        print(
            f"PAPER SPORTSBOOK BET: "
            f"{x['book']} — "
            f"{x['book_team']} "
            f"{x['book_odds']:+d}"
        )

        print()

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
            f"Executable ROI: "
            f"{x['roi'] * 100:.2f}%"
        )

        print("-" * 70)


if __name__ == "__main__":
    main()
