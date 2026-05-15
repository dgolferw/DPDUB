#!/usr/bin/env python3
import argparse
from tabulate import tabulate
import config
from utils.client import get_trading_client
from utils.market import get_bars, get_positions, is_market_open
from utils.orders import calc_order_qty, place_market_order
from strategies.moving_average import MovingAverageCrossover
from strategies.rsi import RSIMeanReversion
from strategies.rebalance import BuyHoldRebalance
STRATEGIES = {"ma": MovingAverageCrossover, "rsi": RSIMeanReversion, "rebalance": BuyHoldRebalance}
def show_account():
    a = get_trading_client().get_account()
    rows = [["Portfolio Value", f"${float(a.portfolio_value):,.2f}"],["Cash", f"${float(a.cash):,.2f}"],["Buying Power", f"${float(a.buying_power):,.2f}"],["Equity", f"${float(a.equity):,.2f}"],["P&L Today", f"${float(a.equity)-float(a.last_equity):,.2f}"],["Status", str(a.status)]]
    print("\n" + "="*40 + "\n  ACCOUNT SUMMARY\n" + "="*40)
    print(tabulate(rows, tablefmt="simple"))
def show_positions():
    positions = get_positions()
    if not positions: print("\n  No open positions.\n"); return
    rows = [[s,p.qty,f"${float(p.avg_entry_price):,.2f}",f"${float(p.current_price):,.2f}",f"${float(p.market_value):,.2f}",f"${float(p.unrealized_pl):,.2f}",f"{float(p.unrealized_plpc)*100:.2f}%"] for s,p in positions.items()]
    print("\n" + "="*70 + "\n  OPEN POSITIONS\n" + "="*70)
    print(tabulate(rows, headers=["Symbol","Qty","Avg Cost","Price","Mkt Value","Unreal P&L","P&L %"], tablefmt="simple"))
def show_status():
    show_account(); show_positions()
    print(f"\n  Market is currently: {'OPEN' if is_market_open() else 'CLOSED'}\n")
def run_strategy(key, tickers, dry_run=False):
    cls = STRATEGIES.get(key)
    if not cls: print(f"Unknown: {key}"); return
    s = cls(tickers)
    print(f"\nRunning: {s.name}\nTickers: {', '.join(tickers)}\n")
    if key == "rebalance": _run_rebalance(tickers, dry_run); return
    bars = get_bars(tickers, days=max(config.MA_LONG_WINDOW, config.RSI_PERIOD)+10)
    signals = s.generate_signals(bars)
    cash = float(get_trading_client().get_account().cash)
    positions = get_positions()
    rows = []; placed = []
    for sym, sig in signals.items():
        action = "-"
        if sig == "buy":
            df = bars.get(sym)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1]); qty = calc_order_qty(cash, price)
                if qty > 0:
                    if not dry_run: placed.append(place_market_order(sym,"buy",qty)); action = f"BUY {qty} @ ~${price:.2f}"
                    else: action = f"[DRY] BUY {qty} @ ~${price:.2f}"
        elif sig == "sell":
            pos = positions.get(sym)
            if pos:
                qty = float(pos.qty)
                if not dry_run: placed.append(place_market_order(sym,"sell",qty)); action = f"SELL {qty}"
                else: action = f"[DRY] SELL {qty}"
        rows.append([sym, sig.upper(), action])
    print(tabulate(rows, headers=["Symbol","Signal","Action"], tablefmt="simple"))
    print(f"\n  {len(placed)} order(s) placed." if placed else "\n  No orders placed.")
def _run_rebalance(tickers, dry_run):
    a = get_trading_client().get_account()
    pv = float(a.portfolio_value); cash = float(a.cash)
    positions = get_positions(); target = pv / len(tickers)
    bars = get_bars(tickers, days=5); rows = []; placed = []
    for sym in tickers:
        df = bars.get(sym)
        if df is None or df.empty: rows.append([sym,"-","-","No data","-"]); continue
        price = float(df["close"].iloc[-1]); pos = positions.get(sym)
        curr = float(pos.market_value) if pos else 0.0; diff = target - curr; qty = abs(diff)/price
        if diff > price*0.01:
            aq = min(qty, cash/price); action = f"BUY {aq:.4f}"
            if not dry_run and aq > 0: placed.append(place_market_order(sym,"buy",aq))
            elif dry_run: action = f"[DRY] {action}"
        elif diff < -price*0.01:
            action = f"SELL {qty:.4f}"
            if not dry_run and pos: placed.append(place_market_order(sym,"sell",min(qty,float(pos.qty))))
            elif dry_run: action = f"[DRY] {action}"
        else: action = "HOLD"
        rows.append([sym, f"${price:.2f}", f"${curr:,.2f}", f"${target:,.2f}", action])
    print(tabulate(rows, headers=["Symbol","Price","Current","Target","Action"], tablefmt="simple"))
    print(f"\n  {len(placed)} order(s) placed." if placed else "\n  No rebalance needed.")
def interactive_menu():
    print("\n" + "="*50 + "\n  ALPACA PAPER TRADING BOT\n" + "="*50)
    tickers = config.DEFAULT_TICKERS
    while True:
        print("\n1. Status  2. MA Strategy  3. RSI Strategy  4. Rebalance  5. Tickers  6. Dry-run  0. Exit")
        c = input("\nSelect: ").strip()
        if c=="0": break
        elif c=="1": show_status()
        elif c=="2": run_strategy("ma", tickers)
        elif c=="3": run_strategy("rsi", tickers)
        elif c=="4": run_strategy("rebalance", tickers)
        elif c=="5":
            tickers = [t.strip() for t in input("Tickers (e.g. AAPL,MSFT): ").upper().split(",") if t.strip()]
            print(f"Set: {tickers}")
        elif c=="6":
            run_strategy(input("Strategy [ma/rsi/rebalance]: ").strip(), tickers, dry_run=True)
        else: print("Invalid.")
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", choices=list(STRATEGIES.keys()))
    p.add_argument("--status", action="store_true")
    p.add_argument("--tickers", default=",".join(config.DEFAULT_TICKERS))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if args.status: show_status()
    elif args.run: run_strategy(args.run, tickers, dry_run=args.dry_run)
    else: interactive_menu()
if __name__ == "__main__":
    main()
