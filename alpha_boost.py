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

# Sector tickers
SPACE_TICKERS = ["RKLB","ASTS","LUNR","KTOS","NOC","LMT"]
TECH_TICKERS = ["NVDA","AMD","MSFT","GOOGL","AVGO","QCOM","INTC","PLTR","TSLA","COIN","IONQ"]
DATACENTER_TICKERS = ["EQIX","DLR","VRT","SMCI","DELL","HPE","GEO","ANET","BE","VST","NRG"]
HEDGE_TICKERS = ["SQQQ"]
DEFAULT_TICKERS = SPACE_TICKERS + TECH_TICKERS + DATACENTER_TICKERS + HEDGE_TICKERS

# Picks & Shovels tiers
TIER1 = ["NVDA","EQIX","VRT","ANET","BE","VST"]
TIER2 = ["AMD","AVGO","SMCI","DLR","NRG","MSFT","INTC","PLTR"]
TIER3 = ["RKLB","ASTS","IONQ","LUNR","KTOS","COIN","TSLA","GEO","SQQQ","NOC","LMT","GOOGL","QCOM","DELL","HPE"]

# RSI settings
RSI_PERIOD = 10
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65
STRONG_OVERSOLD = 25
NORMAL_OVERSOLD = 30
WEAK_OVERSOLD = 35

# Tier-based RSI sell thresholds
TIER1_SELL_RSI = 75
TIER2_SELL_RSI = 68
TIER3_SELL_RSI = 65

# Tier-based order sizing
ORDER_FRACTION_TIER1_STRONG = 0.10
ORDER_FRACTION_TIER1_NORMAL = 0.08
ORDER_FRACTION_TIER2_STRONG = 0.08
ORDER_FRACTION_TIER2_NORMAL = 0.07
ORDER_FRACTION_TIER3 = 0.05
ORDER_FRACTION = 0.07

# Tier-based trailing stops
TIER1_TRAILING_STOP = 6.0
TIER2_TRAILING_STOP = 4.0
TIER3_TRAILING_STOP = 3.0
TRAILING_STOP_PCT = 4.0

# Market regime filter
MARKET_REGIME_TICKER = "SPY"
MARKET_REGIME_MA = 50

# Profit taking
PROFIT_TAKE_PCT = 0.15

# Position concentration
MAX_POSITION_PCT = 0.15

# Time of day - best buy window (ET hour, 24h)
BUY_WINDOW_START = 10
BUY_WINDOW_END = 15

# Other settings
MA_SHORT_WINDOW = 10
MA_LONG_WINDOW = 30
VOLUME_MA_DAYS = 20
SECTOR_ROTATION_DAYS = 5
STOP_LOSS_PCT = 0.05
CAMPAIGN_DAYS = 30
""")
print("config.py done")

# utils/regime.py
open('utils/regime.py','w').write("""import config
from utils.market import get_bars

def get_market_regime():
    bars = get_bars([config.MARKET_REGIME_TICKER], days=config.MARKET_REGIME_MA + 5)
    df = bars.get(config.MARKET_REGIME_TICKER)
    if df is None or df.empty or len(df) < config.MARKET_REGIME_MA:
        return "bull"
    close = df["close"].astype(float)
    current = float(close.iloc[-1])
    ma50 = float(close.rolling(config.MARKET_REGIME_MA).mean().iloc[-1])
    regime = "bull" if current > ma50 else "bear"
    pct = (current - ma50) / ma50 * 100
    print(f"  Market Regime: {regime.upper()} (SPY ${current:.2f} vs 50MA ${ma50:.2f}, {pct:+.1f}%)")
    return regime
""")
print("utils/regime.py done")

# utils/risk.py
open('utils/risk.py','w').write("""import config
from utils.client import get_trading_client
from utils.market import get_positions
from utils.orders import place_market_order

def check_profit_taking():
    positions = get_positions()
    account = get_trading_client().get_account()
    portfolio_value = float(account.portfolio_value)
    taken = []

    for sym, pos in positions.items():
        unreal_pct = float(pos.unrealized_plpc)
        if unreal_pct >= config.PROFIT_TAKE_PCT:
            qty = float(pos.qty)
            sell_qty = round(qty * 0.5, 6)
            if sell_qty > 0:
                place_market_order(sym, "sell", sell_qty)
                taken.append((sym, unreal_pct * 100, sell_qty))
                print(f"  PROFIT TAKE: {sym} up {unreal_pct*100:.1f}% — sold half ({sell_qty} shares)")

    return taken

def check_concentration(sym, qty, price, portfolio_value):
    position_value = qty * price
    if portfolio_value > 0 and (position_value / portfolio_value) > config.MAX_POSITION_PCT:
        max_value = portfolio_value * config.MAX_POSITION_PCT
        max_qty = max_value / price
        return max(round(max_qty, 6), 0)
    return qty
""")
print("utils/risk.py done")

# strategies/rsi.py
open('strategies/rsi.py','w').write("""import pandas as pd
from strategies.base import BaseStrategy
import config

class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion — Picks & Shovels"
    description = "Tier-based RSI with volume, momentum, gap, regime, and concentration filters."

    def __init__(self, tickers, period=config.RSI_PERIOD):
        super().__init__(tickers)
        self.period = period

    def _get_tier(self, sym):
        if sym in config.TIER1:
            return 1
        elif sym in config.TIER2:
            return 2
        return 3

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

    def _get_order_fraction(self, sym, signal):
        tier = self._get_tier(sym)
        if tier == 1:
            return config.ORDER_FRACTION_TIER1_STRONG if signal == "strong_buy" else config.ORDER_FRACTION_TIER1_NORMAL
        elif tier == 2:
            return config.ORDER_FRACTION_TIER2_STRONG if signal == "strong_buy" else config.ORDER_FRACTION_TIER2_NORMAL
        return config.ORDER_FRACTION_TIER3

    def _get_sell_rsi(self, sym):
        tier = self._get_tier(sym)
        if tier == 1: return config.TIER1_SELL_RSI
        elif tier == 2: return config.TIER2_SELL_RSI
        return config.TIER3_SELL_RSI

    def _get_trailing_stop(self, sym):
        tier = self._get_tier(sym)
        if tier == 1: return config.TIER1_TRAILING_STOP
        elif tier == 2: return config.TIER2_TRAILING_STOP
        return config.TIER3_TRAILING_STOP

    def generate_signals(self, bars, regime="bull"):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.period + 1:
                signals[sym] = ("hold", config.ORDER_FRACTION, config.TRAILING_STOP_PCT)
                continue

            close = df["close"].astype(float)
            rsi = self._rsi(close)
            above_ma = self._above_20ma(close)
            vol_ok = self._volume_confirmed(df)
            gap = self._gap_down(df)
            sell_rsi = self._get_sell_rsi(sym)
            trail = self._get_trailing_stop(sym)
            tier = self._get_tier(sym)

            # In bear market: skip Tier 3 buys, only strong signals for Tier 1/2
            if regime == "bear":
                if tier == 3 and sym != "SQQQ":
                    signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                    continue
                if tier in (1, 2) and rsi >= config.STRONG_OVERSOLD:
                    signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                    continue

            if gap:
                signals[sym] = ("hold", config.ORDER_FRACTION, trail)
            elif rsi < config.STRONG_OVERSOLD and vol_ok:
                frac = self._get_order_fraction(sym, "strong_buy")
                signals[sym] = ("strong_buy", frac, trail)
            elif rsi < config.NORMAL_OVERSOLD and above_ma and vol_ok:
                frac = self._get_order_fraction(sym, "buy")
                signals[sym] = ("buy", frac, trail)
            elif rsi < config.WEAK_OVERSOLD and above_ma and vol_ok and tier in (1, 2):
                frac = self._get_order_fraction(sym, "buy")
                signals[sym] = ("buy", frac, trail)
            elif rsi > sell_rsi:
                signals[sym] = ("sell", config.ORDER_FRACTION, trail)
            else:
                signals[sym] = ("hold", config.ORDER_FRACTION, trail)

        # In bear market boost SQQQ
        if regime == "bear" and "SQQQ" in signals:
            signals["SQQQ"] = ("strong_buy", config.ORDER_FRACTION_TIER1_STRONG, config.TIER1_TRAILING_STOP)

        return signals
""")
print("strategies/rsi.py done")

# bot.py
open('bot.py','w').write("""#!/usr/bin/env python3
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
    print("\\n" + "="*40 + "\\n  ACCOUNT SUMMARY\\n" + "="*40)
    print(tabulate(rows, tablefmt="simple"))

def show_positions():
    positions = get_positions()
    if not positions:
        print("\\n  No open positions.\\n")
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
    print("\\n" + "="*80 + "\\n  OPEN POSITIONS\\n" + "="*80)
    print(tabulate(rows, headers=["Symbol","Tier","Qty","Avg Cost","Price","Mkt Value","Unreal P&L","P&L %"], tablefmt="simple"))

def show_status():
    show_account()
    show_positions()
    print(f"\\n  Market: {'OPEN' if is_market_open() else 'CLOSED'}")
    print(f"  Buy window active: {in_buy_window()}")
    print("\\n  Tier 1 (Essential):", ", ".join(config.TIER1))
    print("  Tier 2 (Important):", ", ".join(config.TIER2))
    print("  Tier 3 (Speculative):", ", ".join(config.TIER3))

def run_strategy(tickers, dry_run=False):
    print("\\n--- Pre-run checks ---")

    # Market regime
    regime = get_market_regime()

    # Profit taking check
    print("  Checking profit taking...")
    if not dry_run:
        taken = check_profit_taking()
        if taken:
            print(f"  Took profits on {len(taken)} position(s)")
    else:
        print("  [DRY] Skipping profit taking check")

    # Time of day filter
    if not in_buy_window() and not dry_run:
        print(f"  Outside buy window ({config.BUY_WINDOW_START}AM-{config.BUY_WINDOW_END}PM ET) — skipping new buys")
        return

    # Sector rotation
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
                        place_trailing_stop(sym, qty, trail)
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

    print("\\n" + "="*80)
    print(tabulate(rows, headers=["Symbol","Tier","Signal","Size","Action"], tablefmt="simple"))
    print(f"\\n  {len(placed)} order(s) placed." if placed else "\\n  No orders placed.")
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
""")
print("bot.py done")

print("\nAll files updated! Now run:")
print("git add config.py strategies/rsi.py utils/regime.py utils/risk.py bot.py")
print("git commit -m 'Add market regime, profit taking, concentration limit, buy window'")
print("git push origin main")