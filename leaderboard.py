#!/usr/bin/env python3
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from utils.client import get_trading_client
from utils.market import get_positions

STARTING_EQUITY = 100_000.0
PLAYER_HANDLE = "Dodge"

def build_snapshot():
    client = get_trading_client()
    account = client.get_account()
    positions = get_positions()
    equity = float(account.equity)
    cash = float(account.cash)
    roi_pct = ((equity - STARTING_EQUITY) / STARTING_EQUITY) * 100
    pos_list = [
        {"symbol": sym, "qty": float(p.qty), "market_value": float(p.market_value),
         "unrealized_pl": float(p.unrealized_pl), "unrealized_plpc": float(p.unrealized_plpc)}
        for sym, p in positions.items()
    ]
    return {
        "handle": PLAYER_HANDLE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "equity": equity,
        "cash": cash,
        "roi_pct": round(roi_pct, 4),
        "positions": pos_list,
    }

def post_snapshot(url, snapshot):
    data = json.dumps(snapshot).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=False)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    snapshot = build_snapshot()
    print(f"\n  Handle: {PLAYER_HANDLE}")
    print(f"  Equity: ${snapshot['equity']:,.2f}  ROI: {snapshot['roi_pct']:+.2f}%  Positions: {len(snapshot['positions'])}")
    if args.dry_run or not args.url:
        print("Dry-run: not posted.")
        return
    try:
        result = post_snapshot(args.url, snapshot)
        print(f"Response: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Failed to post: {e}")

if __name__ == "__main__":
    main()
