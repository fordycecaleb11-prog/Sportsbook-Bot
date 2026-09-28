import requests

# Eagles token from our successful diagnostic
TOKEN_ID = (
    "29652429512130463118665284075870201747739909237084592893331546208800561253258"
)

URL = "https://clob.polymarket.com/book"

params = {
    "token_id": TOKEN_ID
}

response = requests.get(
    URL,
    params=params,
    timeout=30,
)

print("STATUS:", response.status_code)

response.raise_for_status()

data = response.json()

print()
print("FULL ORDER BOOK:")
print("=" * 70)
print(data)

print()
print("=" * 70)

bids = data.get("bids", [])
asks = data.get("asks", [])

print(f"BIDS: {len(bids)}")
print(f"ASKS: {len(asks)}")

print()

if bids:
    print("FIRST BID:")
    print(bids[0])

if asks:
    print()
    print("FIRST ASK:")
    print(asks[0])
