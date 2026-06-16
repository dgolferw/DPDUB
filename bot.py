#!/usr/bin/env python3
import argparse
import time
from datetime import datetime
import pytz
from tabulate import tabulate
import config
from utils.client import get_trading_client
from utils.market import get_bars, get_positions, is_market_open
from utils.orders import calc_order_qty, place_market_order, place_trailing_stop, cancel_open_trailing_stops, cancel_orphaned_trailing_stops
from utils.sector import get_active_tickers
from utils.regime import get_market_regime, get_short_term_momentum
from utils.risk import check_concentration, check_profit_taking, check_stop_losses
from strategies.rsi import RSIMeanReversion

ET = pytz.timezone("America/New_York")
MIN_QTY = 0.001
CASH_FLOOR_PCT = 0.05

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

def _trail_pct(sym):
    if sym in config.TIER1: return config.TIER1_TRAILING_STOP
    if sym in config.TIER2: return config.TIER2_TRAILING_STOP
    return config.TIER3_TRAILING_STOP

def audit_trailing_stops(positions):
    from alpaca.trading.requests import GetOrdersRequest
    from alpaca.trading.enums import QueryOrderStatus
    from utils.client import get_trading_client
    client = get_trading_client()
    for sym, pos in positions.items():
        qty = float(pos.qty)
        if qty < MIN_QTY:
            continue
        stop_qty = int(qty)
        if stop_qty < 1:
            continue
        open_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[sym]))
        has_stop = any(o.side.value == "sell" for o in open_orders)
        if not has_stop:
            try:
                place_trailing_stop(sym, stop_qty, _trail_pct(sym))
                print(f"  Placed missing trailing stop for {sym} ({stop_qty} shares @ {_trail_pct(sym)}%)")
            except Exception as e:
                print(f"  Trailing stop audit skipped for {sym}: {e}")

def clear_losers_for_sqqq(real_positions, stopped, dry_run):
    """When market is declining, sell all losing tech longs to fund SQQQ."""
    cleared = []
    for sym, pos in real_positions.items():
        if sym in stopped or sym in ("SQQQ", "TQQQ", "SOXL", "INTC"):
            continue
        plpc = float(pos.unrealized_plpc)
        if plpc < 0:
            qty = float(pos.qty)
            print(f"  CLEAR LOSER: {sym} ({plpc*100:.1f}%) — freeing capital for SQQQ")
            if not dry_run:
                try:
                    cancel_open_trailing_stops(sym)
                    place_market_order(sym, "sell", qty)
                    cleared.append(sym)
                except Exception as e:
                    print(f"  Clear skipped for {sym}: {e}")
            else:
                cleared.append(sym)
    return cleared

def run_strategy(tickers, dry_run=False):
    print("\n--- Pre-run checks ---")
    regime = get_market_regime()
    momentum = get_short_term_momentum()
    stopped = []

    print("  Cancelling orphaned trailing stops...")
    if not dry_run:
        positions = get_positions()
        cancel_orphaned_trailing_stops(set(positions.keys()))

    print("  Checking stop losses...")
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

    positions = get_positions()
    real_positions = {s: p for s, p in positions.items() if float(p.qty) >= MIN_QTY}

    # When declining: sell all losers to fund SQQQ
    if momentum == "declining" and not dry_run:
        cleared = clear_losers_for_sqqq(real_positions, stopped, dry_run)
        stopped.extend(cleared)
        if cleared:
            positions = get_positions()
            real_positions = {s: p for s, p in positions.items() if float(p.qty) >= MIN_QTY}

    # Trim to MAX_POSITIONS
    if not dry_run:
        if len(real_positions) > config.MAX_POSITIONS:
            excess = len(real_positions) - config.MAX_POSITIONS
            worst = sorted(real_positions.items(), key=lambda x: float(x[1].unrealized_plpc))[:excess]
            for sym, pos in worst:
                qty = float(pos.qty)
                print(f"  TRIM: {sym} ({float(pos.unrealized_plpc)*100:.1f}%) — over {config.MAX_POSITIONS} position limit")
                try:
                    cancel_open_trailing_stops(sym)
                    place_market_order(sym, "sell", qty)
                    stopped.append(sym)
                except Exception as e:
                    print(f"  TRIM skipped for {sym}: {e}")

    tickers = list(config.DEFAULT_TICKERS)
    if "SQQQ" not in tickers:
        tickers.append("SQQQ")
    if "TQQQ" not in tickers:
        tickers.append("TQQQ")
    if "SOXL" not in tickers:
        tickers.append("SOXL")

    all_syms = list(set(tickers) | set(real_positions.keys()))
    strategy = RSIMeanReversion(all_syms)
    bars = get_bars(all_syms, days=max(config.MA_LONG_WINDOW, config.RSI_PERIOD, config.VOLUME_MA_DAYS)+5)
    signals = strategy.generate_signals(bars, regime=regime, momentum=momentum)

    account = get_trading_client().get_account()
    cash = float(account.cash)
    portfolio_value = float(account.portfolio_value)
    cash_floor = portfolio_value * CASH_FLOOR_PCT
    rows = []
    placed = []

    for sym, (signal, fraction, trail) in signals.items():
        if sym in stopped:
            continue
        tier = 1 if sym in config.TIER1 else (2 if sym in config.TIER2 else 3)
        action = "-"
        if signal in ("buy", "strong_buy"):
            df = bars.get(sym)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1])
                existing_pos = real_positions.get(sym)
                if existing_pos:
                    current_alloc = float(existing_pos.market_value) / portfolio_value
                    if current_alloc >= fraction * 0.90:
                        action = f"[SKIP] already {current_alloc*100:.1f}% allocated (target {fraction*100:.0f}%)"
                        rows.append([sym, f"T{tier}", signal.upper(), f"{fraction*100:.0f}%", action])
                        continue
                qty = calc_order_qty(cash, price, fraction)
                qty = check_concentration(sym, qty, price, portfolio_value)
                if qty > 0:
                    label = "STRONG BUY" if signal == "strong_buy" else "BUY"
                    if momentum == "declining" and signal != "strong_buy":
                        action = f"[SKIP] {label} — market declining"
                    elif cash <= cash_floor and signal != "strong_buy":
                        action = f"[SKIP] {label} — cash floor"
                    elif not dry_run:
                        place_market_order(sym, "buy", qty)
                        stop_qty = int(float(existing_pos.qty)) if existing_pos else int(qty)
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
            pos = real_positions.get(sym)
            if pos:
                qty = float(pos.qty)
                sell_qty = qty if sym in ("SQQQ", "TQQQ", "SOXL") else round(qty * 0.5, 6)
                remaining_qty = round(qty - sell_qty, 6)
                if sell_qty >= MIN_QTY:
                    label = "SELL ALL" if sym in ("SQQQ", "TQQQ", "SOXL") else "SELL HALF"
                    if not dry_run:
                        try:
                            cancel_open_trailing_stops(sym)
                            place_market_order(sym, "sell", sell_qty)
                            if sym not in ("SQQQ", "TQQQ", "SOXL") and int(remaining_qty) > 0:
                                try:
                                    place_trailing_stop(sym, int(remaining_qty), trail)
                                except Exception as e:
                                    print(f"  Trailing stop skipped for {sym}: {e}")
                            action = f"{label} {sell_qty}"
                            placed.append(sym)
                        except Exception as e:
                            print(f"  Sell skipped for {sym}: {e}")
                    else:
                        action = f"[DRY] {label} {sell_qty}"
        rows.append([sym, f"T{tier}", signal.upper(), f"{fraction*100:.0f}%", action])

    print("\n" + "="*80)
    print(tabulate(rows, headers=["Symbol","Tier","Signal","Size","Action"], tablefmt="simple"))
    print(f"\n  {len(placed)} order(s) placed." if placed else "\n  No orders placed.")
    print(f"  Regime: {regime.upper()}  |  Momentum: {momentum.upper()}  |  Cash remaining: ${cash:,.2f}")

    if not dry_run and placed:
        print("\n  Auditing trailing stops...")
        time.sleep(2)
        audit_trailing_stops(get_positions())

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
