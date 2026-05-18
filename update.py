import os

# config.py
open('config.py','w').write("""import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
if not API_KEY or not SECRET_KEY:
    raise EnvironmentError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
SPACE_TICKERS = ["RKLB","ASTS","LUNR","KTOS","NOC","LMT"]
TECH_TICKERS = ["NVDA","AMD","MSFT","GOOGL","AVGO","QCOM","INTC","PLTR","TSLA","COIN","IONQ"]
DATACENTER_TICKERS = ["EQIX","DLR","VRT","SMCI","DELL","HPE","GEO"]
HEDGE_TICKERS = ["SQQQ"]
DEFAULT_TICKERS = SPACE_TICKERS + TECH_TICKERS + DATACENTER_TICKERS + HEDGE_TICKERS
MA_SHORT_WINDOW = 10
MA_LONG_WINDOW = 30
RSI_PERIOD = 10
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65
STRONG_OVERSOLD = 25
NORMAL_OVERSOLD = 30
WEAK_OVERSOLD = 35
ORDER_FRACTION = 0.07
ORDER_FRACTION_WEAK = 0.05
ORDER_FRACTION_NORMAL = 0.07
ORDER_FRACTION_STRONG = 0.10
TRAILING_STOP_PCT = 4.0
STOP_LOSS_PCT = 0.05
VOLUME_MA_DAYS = 20
SECTOR_ROTATION_DAYS = 5
CAMPAIGN_DAYS = 30
""")
print("config.py done")

# strategies/rsi.py
open('strategies/rsi.py','w').write("""import pandas as pd
from strategies.base import BaseStrategy
import config

class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion"
    description = "RSI with volume confirmation, momentum filter, gap filter, and dynamic sizing."

    def __init__(self, tickers, period=config.RSI_PERIOD):
        super().__init__(tickers)
        self.period = period

    def _rsi(self, close):
        d = close.diff().dropna()
        rs = d.clip(lower=0).rolling(self.period).mean() / (-d.clip(upper=0)).rolling(self.period).mean().replace(0, float("inf"))
        return float((100 - 100/(1+rs)).iloc[-1])

    def _above_20ma(self, close):
        if len(close) < 20:
            return True
        return float(close.iloc[-1]) > float(close.rolling(20).mean().iloc[-1])

    def _volume_confirmed(self, df):
        if "volume" not in df.columns or len(df) < config.VOLUME_MA_DAYS:
            return True
        avg_vol = df["volume"].rolling(config.VOLUME_MA_DAYS).mean().iloc[-1]
        return float(df["volume"].iloc[-1]) > float(avg_vol)

    def _gap_down(self, df):
        if len(df) < 2:
            return False
        prev_close = float(df["close"].iloc[-2])
        open_price = float(df["open"].iloc[-1]) if "open" in df.columns else prev_close
        return (open_price - prev_close) / prev_close < -0.03

    def generate_signals(self, bars):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.period + 1:
                signals[sym] = ("hold", config.ORDER_FRACTION)
                continue
            close = df["close"].astype(float)
            rsi = self._rsi(close)
            above_ma = self._above_20ma(close)
            vol_ok = self._volume_confirmed(df)
            gap = self._gap_down(df)
            if gap:
                signals[sym] = ("hold", config.ORDER_FRACTION)
            elif rsi < config.STRONG_OVERSOLD and vol_ok:
                signals[sym] = ("strong_buy", config.ORDER_FRACTION_STRONG)
            elif rsi < config.NORMAL_OVERSOLD and above_ma and vol_ok:
                signals[sym] = ("buy", config.ORDER_FRACTION_NORMAL)
            elif rsi < config.WEAK_OVERSOLD and above_ma and vol_ok:
                signals[sym] = ("buy", config.ORDER_FRACTION_WEAK)
            elif rsi > config.RSI_OVERBOUGHT:
                signals[sym] = ("sell", config.ORDER_FRACTION)
            else:
                signals[sym] = ("hold", config.ORDER_FRACTION)
        return signals
""")
print("strategies/rsi.py done")

# utils/orders.py
open('utils/orders.py','w').write("""from alpaca.trading.requests import MarketOrderRequest, TrailingStopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from utils.client import get_trading_client
import config

def place_market_order(symbol, side, qty):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=round(qty, 6),
        side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    result = get_trading_client().submit_order(order)
    return {"id": str(result.id), "symbol": symbol, "side": side, "qty": qty, "status": str(result.status)}

def place_trailing_stop(symbol, qty):
    order = TrailingStopOrderRequest(
        symbol=symbol,
        qty=round(qty, 6),
        side=OrderSide.SELL,
        time_in_force=TimeInForce.GTC,
        trail_percent=config.TRAILING_STOP_PCT,
    )
    result = get_trading_client().submit_order(order)
    return {"id": str(result.id), "symbol": symbol, "trail_pct": config.TRAILING_STOP_PCT}

def calc_order_qty(cash, price, fraction=config.ORDER_FRACTION):
    return max(round((cash * fraction) / price, 6), 0)
""")
print("utils/orders.py done")

# utils/sector.py
open('utils/sector.py','w').write("""import config
from utils.market import get_bars

def get_sector_performance():
    all_bars = get_bars(config.DEFAULT_TICKERS, days=config.SECTOR_ROTATION_DAYS + 2)
    sectors = {
        "space": config.SPACE_TICKERS,
        "tech": config.TECH_TICKERS,
        "datacenter": config.DATACENTER_TICKERS,
        "hedge": config.HEDGE_TICKERS,
    }
    perf = {}
    for sector, tickers in sectors.items():
        returns = []
        for sym in tickers:
            df = all_bars.get(sym)
            if df is None or df.empty or len(df) < 2:
                continue
            ret = (float(df["close"].iloc[-1]) - float(df["close"].iloc[0])) / float(df["close"].iloc[0])
            returns.append(ret)
        perf[sector] = sum(returns) / len(returns) if returns else 0.0
    return perf

def get_active_tickers():
    perf = get_sector_performance()
    sorted_sectors = sorted(perf.items(), key=lambda x: x[1], reverse=True)
    sectors = {
        "space": config.SPACE_TICKERS,
        "tech": config.TECH_TICKERS,
        "datacenter": config.DATACENTER_TICKERS,
        "hedge": config.HEDGE_TICKERS,
    }
    print("\\nSector Performance ({}d):".format(config.SECTOR_ROTATION_DAYS))
    active = list(config.HEDGE_TICKERS)
    for i, (sector, ret) in enumerate(sorted_sectors):
        print(f"  {sector:12s} {ret*100:+.2f}%")
        if i < 3:
            active.extend(sectors[sector])
    return list(set(active))
""")
print("utils/sector.py done")

# bot.py
open('bot.py','w').write("""#!/usr/bin/env python3
import argparse
from tabulate import tabulate
import config
from utils.client import get_trading_client
from utils.market import get_bars, get_positions, is_market_open
from utils.orders import calc_order_qty, place_market_order, place_trailing_stop
from utils.sector import get_active_tickers
from strategies.rsi import RSIMeanReversion

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
    print("\\n" + "="*40 + "\\n  ACCOUNT SUMMARY\\n" + "="*40)
    print(tabulate(rows, tablefmt="simple"))

def show_positions():
    positions = get_positions()
    if not positions:
        print("\\n  No open positions.\\n")
        return
    rows = [[s, p.qty, f"${float(p.avg_entry_price):,.2f}", f"${float(p.current_price):,.2f}",
             f"${float(p.market_value):,.2f}", f"${float(p.unrealized_pl):,.2f}",
             f"{float(p.unrealized_plpc)*100:.2f}%"] for s, p in positions.items()]
    print("\\n" + "="*70 + "\\n  OPEN POSITIONS\\n" + "="*70)
    print(tabulate(rows, headers=["Symbol","Qty","Avg Cost","Price","Mkt Value","Unreal P&L","P&L %"], tablefmt="simple"))

def show_status():
    show_account()
    show_positions()
    print(f"\\n  Market: {'OPEN' if is_market_open() else 'CLOSED'}\\n")

def run_strategy(tickers, dry_run=False):
    print("\\nFetching sector rotation...")
    active = get_active_tickers()
    tickers = [t for t in tickers if t in active] or tickers
    print(f"Trading {len(tickers)} tickers after sector filter")

    strategy = RSIMeanReversion(tickers)
    bars = get_bars(tickers, days=max(config.MA_LONG_WINDOW, config.RSI_PERIOD, config.VOLUME_MA_DAYS)+5)
    signals = strategy.generate_signals(bars)

    account = get_trading_client().get_account()
    cash = float(account.cash)
    positions = get_positions()
    rows = []
    placed = []

    for sym, (signal, fraction) in signals.items():
        action = "-"
        if signal in ("buy", "strong_buy"):
            df = bars.get(sym)
            if df is not None and not df.empty:
                price = float(df["close"].iloc[-1])
                qty = calc_order_qty(cash, price, fraction)
                if qty > 0:
                    label = "STRONG BUY" if signal == "strong_buy" else "BUY"
                    if not dry_run:
                        place_market_order(sym, "buy", qty)
                        place_trailing_stop(sym, qty)
                        cash -= qty * price
                        action = f"{label} {qty} @ ~${price:.2f} +trail4%"
                        placed.append(sym)
                    else:
                        action = f"[DRY] {label} {qty} @ ~${price:.2f}"
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
        rows.append([sym, signal.upper(), f"{fraction*100:.0f}%", action])

    print(tabulate(rows, headers=["Symbol","Signal","Size","Action"], tablefmt="simple"))
    print(f"\\n  {len(placed)} order(s) placed." if placed else "\\n  No orders placed.")

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
""")
print("bot.py done")

# GitHub Actions workflow
os.makedirs('.github/workflows', exist_ok=True)
open('.github/workflows/trade.yml','w').write("""name: Daily Trading Bot

on:
  schedule:
    - cron: "31 13 * * 1-5"
    - cron: "30 19 * * 1-5"
  workflow_dispatch:

jobs:
  trade:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run bot
        env:
          ALPACA_API_KEY: ${{ secrets.ALPACA_API_KEY }}
          ALPACA_SECRET_KEY: ${{ secrets.ALPACA_SECRET_KEY }}
          ALPACA_BASE_URL: https://paper-api.alpaca.markets
        run: python bot.py --run
""")
print(".github/workflows/trade.yml done")

print("\nAll files updated! Now run:")
print("git add config.py strategies/rsi.py utils/orders.py utils/sector.py bot.py .github/workflows/trade.yml")
print("git commit -m 'Add volume filter, trailing stops, sector rotation, dynamic sizing'")
print("git push origin main")