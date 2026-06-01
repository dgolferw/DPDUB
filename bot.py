#!/usr/bin/env python3
import argparse
from datetime import datetime
import pytz
from tabulate import tabulate
import config
from utils.client import get_trading_client
from utils.market import get_bars, get_positions, is_market_open
from utils.orders import calc_order_qty, place_market_order, place_trailing_stop, cancel_open_trailing_stops, cancel_orphaned_trailing_stops
from utils.sector import get_active_tickers
from utils.regime import get_market_regime
from utils.risk import check_concentration, check_profit_taking, check_stop_losses, rotate_losers_to_cash
from strategies.rsi import RSIMeanReversion

ET = pytz.timezone("America/New_York")

def in_buy_window():
    now = datetime.now(ET)
    return config.BUY_WINDOW_START <= now.hour < config.BUY_WINDOW_END

def show_account():
    a = get_trading_client().get_account()
    rows = [
        ["Portfolio Value", f"${float(a.portfolio_value):,.2f}"],
        ["Cash", f"${float(a.cash):,.2f}"],
        ["Buying Power", f"${float(a.buying_power):,.2f}"],
        ["Equity", f"${float(a.equity):,.2f}"],
        ["P&L Today", f"${float(a.equity)-float(a.last_equity):,.2f}"],
        ["Status", str(a.status)],
    ]
    print("\n" + "="*40 + "\n  ACCOUNT SUMMARY\n" + "="*40)
    print(tabulate(rows, tablefmt="simple"))

def show_positions():
    positions = get_positions()
    if not positions:
        print("\n  No open positions.\n")
        return
    rows = []
    for s, p in positions.items():
        tier = 1 if s in config.TIER1 else (2 if s in config.TIER2 else 3)
        rows.append([s, f"T{tier}", p.qty,
                     f"${float(p.avg_entry_price):,.2f}",
                     f"${float(p.current_price):,.2f}",
                     f"${float(p.market_value):,.2f}",
                     f"${float(p.unrealized_pl):,.2f}",
                     f"{float(p.unrealized_plpc)*100:.2f}%"])
    print("\n" + "="*80 + "\n  OPEN POSITIONS\n" + "="*80)
    print(tabulate(rows, headers=["Symbol","Tier","Qty","Avg Cost","Price","Mkt Value","Unreal P&L","P&L %"], tablefmt="simple"))

def show_status():
    show_account()
    show_positions()
    print(f"\n  Market: {'OPEN' if is_market_open() else 'CLOSED'}")
    print(f"  Buy window active: {in_buy_window()}")

def run_strategy(tickers, dry_run=False):
    print("\n--- Pre-run checks ---")
    regime = get_market_regime()

    print("  Cancelling orphaned trailing stops...")
    if not dry_run:
        positions = get_positions()
        cancel_orphaned_trailing_stops(set(positions.keys()))

    print("  Checking stop losses...")
    stopped = []
    if not dry_run:
        stopped = check_stop_losses()
        if stopped:
            print(f"  Stop loss triggered on {stopped}")

    print("  Checking profit taking...")
    if not dry_run:
        taken = check_profit_taking()
        if taken:
            print(f"  Took profits on {len(taken)} position(s)")

    if not in_buy_window() and not dry_run:
        print(f"  Outside buy window - skipping new buys")
        return

    print("  Fetching sector rotation...")
    active = get_active_tickers()
    tickers = [t for t in tickers if t in active] or tickers
    print(f"  Trading {len(tickers)} tickers after sector filter")

    strategy = RSIMeanReversion(tickers)
    bars = get_bars(tickers, days=max(config.MA_LONG_WINDOW, config.RSI_PERIOD, config.VOLUME_MA_DAYS)+5)
    signals = strategy.generate_signals(bars, regime=regime)

    account = get_trading_client().get_account()
    cash = float(account.cash)
    portfolio_value = float(account.portfolio_value)
    positions = get_positions()
    rows = []
    placed = []

    print("  Rotating losers to fund winners...")
    if not dry_run:
        cash, rotated = rotate_losers_to_cash(positions, signals, cash, portfolio_value, exclude=stopped)
    else:
        rotated = []

    for sym, (signal, fraction, trail) in signals.items():
        if sym in rotated:
            continue
        tier = 1 if sym in config.TIER1 else (2 if sym in config.TIER2 else 3)
        action = "-"
        if signal in ("buy", "strong_buy"):
            df = bars.get(sym)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1])
                qty = calc_order_qty(cash, price, fraction)
                qty = check_concentration(sym, qty, price, portfolio_value)
                if qty > 0:
                    label = "STRONG BUY" if signal == "strong_buy" else "BUY"
                    if not dry_run:
                        place_market_order(sym, "buy", qty)
                        existing_pos = positions.get(sym)
                        stop_qty = int(float(existing_pos.qty)) if existing_pos else 0
                        if stop_qty > 0:
                            try:
                                place_trailing_stop(sym, stop_qty, trail)
                            except Exception as e:
                                print(f"  Trailing stop skipped for {sym}: {e}")
                        cash -= qty * price
                        action = f"{label} {qty} @ ~${price:.2f} trail={trail}%"
                        placed.append(sym)
                    else:
                        action = f"[DRY] {label} {qty} @ ~${price:.2f} trail={trail}%"
        elif signal == "sell":
            pos = positions.get(sym)
            if pos:
                qty = float(pos.qty)
                sell_qty = round(qty * 0.5, 6)
                remaining_qty = round(qty - sell_qty, 6)
                if not dry_run:
                    cancel_open_trailing_stops(sym)
                    place_market_order(sym, "sell", sell_qty)
                    if int(remaining_qty) > 0:
                        try:
                            place_trailing_stop(sym, int(remaining_qty), trail)
                        except Exception as e:
                            print(f"  Trailing stop skipped for {sym}: {e}")
                    action = f"SELL HALF {sell_qty} trail={trail}%"
                    placed.append(sym)
                else:
                    action = f"[DRY] SELL HALF {sell_qty} trail={trail}%"
        rows.append([sym, f"T{tier}", signal.upper(), f"{fraction*100:.0f}%", action])

    # Add to winning positions that are up 8-12% with a hold signal
    for sym, pos in positions.items():
        if sym in rotated:
            continue
        plpc = float(pos.unrealized_plpc)
        if 0.08 <= plpc < config.PROFIT_TAKE_PCT and signals.get(sym, ("hold",))[0] == "hold":
            df = bars.get(sym)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1])
                qty = calc_order_qty(cash, price, 0.06)
                qty = check_concentration(sym, qty, price, portfolio_value)
                if qty > 0:
                    tier = 1 if sym in config.TIER1 else (2 if sym in config.TIER2 else 3)
                    if not dry_run:
                        place_market_order(sym, "buy", qty)
                        cash -= qty * price
                        placed.append(sym)
                        action = f"ADD {qty} @ ~${price:.2f} (up {plpc*100:.1f}%)"
                    else:
                        action = f"[DRY] ADD {qty} @ ~${price:.2f} (up {plpc*100:.1f}%)"
                    rows.append([sym, f"T{tier}", "ADD", "6%", action])

    print("\n" + "="*80)
    print(tabulate(rows, headers=["Symbol","Tier","Signal","Size","Action"], tablefmt="simple"))
    print(f"\n  {len(placed)} order(s) placed." if placed else "\n  No orders placed.")
    print(f"  Regime: {regime.upper()}  |  Cash remaining: ${cash:,.2f}")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="store_true", default=True)
    p.add_argument("--status", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--tickers", default=",".join(config.DEFAULT_TICKERS))
    args = p.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.status:
        show_status()
    else:
        run_strategy(tickers, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
