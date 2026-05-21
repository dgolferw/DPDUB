#!/usr/bin/env python3
import argparse
import json
import os
import urllib.request
from utils.client import get_trading_client
from utils.market import get_positions

STARTING_EQUITY = 100_000.0
PLAYER_HANDLE = "Dodge"
SNAPSHOT_URL = "https://32.194.248.231.nip.io/api/snapshot"

def build_snapshot():
    client = get_trading_client()
    account = client.get_account()
    positions = get_positions()
    equity = float(account.equity)
    cash = float(account.cash)
    last_equity = float(account.last_equity) if account.last_equity else equity
    day_pnl = round(equity - last_equity, 4)
    roi_pct = ((equity - STARTING_EQUITY) / STARTING_EQUITY) * 100
    pos_list = [
        {"symbol": sym, "qty": float(p.qty), "market_value": float(p.market_value),
         "unrealized_pl": float(p.unrealized_pl), "unrealized_plpc": float(p.unrealized_plpc)}
        for sym, p in positions.items()
    ]
    return {
        "equity": equity,
        "cash": cash,
        "day_pnl": day_pnl,
        "num_positions": len(pos_list),
        "positions_json": json.dumps(pos_list),
        "_handle": PLAYER_HANDLE,
        "_roi_pct": round(roi_pct, 4),
    }

def post_snapshot(snapshot, token):
    payload = {k: v for k, v in snapshot.items() if not k.startswith("_")}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        SNAPSHOT_URL, data=data,
        headers={"Content-Type": "application/json", "X-User-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("LEADERBOARD_TOKEN", "")

    snapshot = build_snapshot()
    print(f"\n  Handle : {snapshot['_handle']}")
    print(f"  Equity : ${snapshot['equity']:,.2f}  ROI: {snapshot['_roi_pct']:+.2f}%"
          f"  Day P&L: ${snapshot['day_pnl']:,.2f}  Positions: {snapshot['num_positions']}")

    if args.dry_run or not token:
        print("Dry-run / no token: not posted.")
        return

    try:
        result = post_snapshot(snapshot, token)
        print(f"Response: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"Failed to post: {e}")

if __name__ == "__main__":
    main()
