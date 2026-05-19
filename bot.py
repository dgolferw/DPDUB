#!/usr/bin/env python3
import argparse
from datetime import datetime
import pytz
from tabulate import tabulate
import config
from utils.client import get_trading_client
from utils.market import get_bars, get_positions, is_market_open
from utils.orders import calc_order_qty, place_market_order, place_trailing_stop
from utils.sector import get_active_tickers
from utils.regime import get_market_regime
from utils.risk import check_profit_taking, check_concentration
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

    for sym, (signal, fraction, trail) in signals.items():
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
                        stop_qty = int(qty)
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
                if not dry_run:
                    place_market_order(sym, "sell", qty)
                    action = f"SELL {qty}"
                    placed.append(sym)
                else:
                    action = f"[DRY] SELL {qty}"
        rows.append([sym, f"T{tier}", signal.upper(), f"{fraction*100:.0f}%", action])

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
