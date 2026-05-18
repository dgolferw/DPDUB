import os

files = {
"requirements.txt": """alpaca-py>=0.43.0
pandas>=2.0.0
numpy>=1.24.0
tabulate>=0.9.0
python-dotenv>=1.0.0
schedule>=1.2.0
pytz>=2024.1
""",
".env": """ALPACA_API_KEY=PKWDAPU26Z6TRNRJPVNAFZWPIH
ALPACA_SECRET_KEY=5ax9LmrM19Nqp7bVrs3YKBX71aJsgknLSEXZ4YvmzQCZ
ALPACA_BASE_URL=https://paper-api.alpaca.markets
""",
"config.py": """import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
if not API_KEY or not SECRET_KEY:
    raise EnvironmentError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")
SPACE_TICKERS = ["RKLB","ASTS","LUNR","KTOS","NOC","LMT"]
TECH_TICKERS = ["NVDA","AMD","MSFT","GOOGL","AVGO","QCOM"]
DATACENTER_TICKERS = ["EQIX","DLR","VRT","SMCI","DELL","HPE"]
DEFAULT_TICKERS = SPACE_TICKERS + TECH_TICKERS + DATACENTER_TICKERS
MA_SHORT_WINDOW = 10
MA_LONG_WINDOW = 30
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
ORDER_FRACTION = 0.1
CAMPAIGN_DAYS = 30
""",
"utils/__init__.py": "",
"utils/client.py": """from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
import config
_trading_client = None
_data_client = None
def get_trading_client():
    global _trading_client
    if _trading_client is None:
        _trading_client = TradingClient(api_key=config.API_KEY, secret_key=config.SECRET_KEY, paper=True)
    return _trading_client
def get_data_client():
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(api_key=config.API_KEY, secret_key=config.SECRET_KEY)
    return _data_client
""",
"utils/market.py": """from datetime import datetime, timedelta, timezone
import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from utils.client import get_data_client, get_trading_client
def is_market_open():
    return get_trading_client().get_clock().is_open
def get_account():
    return get_trading_client().get_account()
def get_bars(symbols, days=60):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    bars = get_data_client().get_stock_bars(StockBarsRequest(symbol_or_symbols=symbols, timeframe=TimeFrame.Day, start=start, end=end))
    result = {}
    for sym in symbols:
        try:
            df = bars[sym].df if hasattr(bars[sym], "df") else pd.DataFrame(bars[sym])
            result[sym] = df
        except (KeyError, TypeError):
            result[sym] = pd.DataFrame()
    return result
def get_positions():
    return {p.symbol: p for p in get_trading_client().get_all_positions()}
""",
"utils/orders.py": """from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from utils.client import get_trading_client
import config
def place_market_order(symbol, side, qty):
    order = MarketOrderRequest(symbol=symbol, qty=round(qty,6), side=OrderSide.BUY if side.lower()=="buy" else OrderSide.SELL, time_in_force=TimeInForce.DAY)
    result = get_trading_client().submit_order(order)
    return {"id": str(result.id), "symbol": symbol, "side": side, "qty": qty, "status": str(result.status)}
def calc_order_qty(cash, price, fraction=config.ORDER_FRACTION):
    return max(round((cash * fraction) / price, 6), 0)
""",
"strategies/__init__.py": "",
"strategies/base.py": """from abc import ABC, abstractmethod
import pandas as pd
class BaseStrategy(ABC):
    name = "Base"
    description = ""
    def __init__(self, tickers):
        self.tickers = tickers
    @abstractmethod
    def generate_signals(self, bars):
        pass
""",
"strategies/moving_average.py": """import pandas as pd
from strategies.base import BaseStrategy
import config
class MovingAverageCrossover(BaseStrategy):
    name = "Moving Average Crossover"
    description = f"Buy when {config.MA_SHORT_WINDOW}-day MA crosses above {config.MA_LONG_WINDOW}-day MA; sell when it crosses below."
    def __init__(self, tickers, short_window=config.MA_SHORT_WINDOW, long_window=config.MA_LONG_WINDOW):
        super().__init__(tickers)
        self.short_window = short_window
        self.long_window = long_window
    def generate_signals(self, bars):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.long_window:
                signals[sym] = "hold"; continue
            close = df["close"].astype(float)
            s = close.rolling(self.short_window).mean()
            l = close.rolling(self.long_window).mean()
            if s.iloc[-2] <= l.iloc[-2] and s.iloc[-1] > l.iloc[-1]: signals[sym] = "buy"
            elif s.iloc[-2] >= l.iloc[-2] and s.iloc[-1] < l.iloc[-1]: signals[sym] = "sell"
            else: signals[sym] = "hold"
        return signals
""",
"strategies/rsi.py": """import pandas as pd
from strategies.base import BaseStrategy
import config
class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion"
    description = f"Buy when RSI({config.RSI_PERIOD}) < {config.RSI_OVERSOLD}; sell when RSI > {config.RSI_OVERBOUGHT}."
    def __init__(self, tickers, period=config.RSI_PERIOD, oversold=config.RSI_OVERSOLD, overbought=config.RSI_OVERBOUGHT):
        super().__init__(tickers)
        self.period = period; self.oversold = oversold; self.overbought = overbought
    def _rsi(self, close):
        d = close.diff().dropna()
        rs = d.clip(lower=0).rolling(self.period).mean() / (-d.clip(upper=0)).rolling(self.period).mean().replace(0, float("inf"))
        return float((100 - 100/(1+rs)).iloc[-1])
    def generate_signals(self, bars):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.period+1: signals[sym] = "hold"; continue
            rsi = self._rsi(df["close"].astype(float))
            if rsi < self.oversold: signals[sym] = "buy"
            elif rsi > self.overbought: signals[sym] = "sell"
            else: signals[sym] = "hold"
        return signals
""",
"strategies/rebalance.py": """from strategies.base import BaseStrategy
class BuyHoldRebalance(BaseStrategy):
    name = "Buy & Hold Rebalance"
    description = "Maintain equal-weight allocation across tickers."
    def generate_signals(self, bars):
        return {sym: "hold" for sym in self.tickers}
""",
"bot.py": open(r"C:\does_not_exist", "r").read() if False else """#!/usr/bin/env python3
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
    print("\\n" + "="*40 + "\\n  ACCOUNT SUMMARY\\n" + "="*40)
    print(tabulate(rows, tablefmt="simple"))
def show_positions():
    positions = get_positions()
    if not positions: print("\\n  No open positions.\\n"); return
    rows = [[s,p.qty,f"${float(p.avg_entry_price):,.2f}",f"${float(p.current_price):,.2f}",f"${float(p.market_value):,.2f}",f"${float(p.unrealized_pl):,.2f}",f"{float(p.unrealized_plpc)*100:.2f}%"] for s,p in positions.items()]
    print("\\n" + "="*70 + "\\n  OPEN POSITIONS\\n" + "="*70)
    print(tabulate(rows, headers=["Symbol","Qty","Avg Cost","Price","Mkt Value","Unreal P&L","P&L %"], tablefmt="simple"))
def show_status():
    show_account(); show_positions()
    print(f"\\n  Market is currently: {'OPEN' if is_market_open() else 'CLOSED'}\\n")
def run_strategy(key, tickers, dry_run=False):
    cls = STRATEGIES.get(key)
    if not cls: print(f"Unknown: {key}"); return
    s = cls(tickers)
    print(f"\\nRunning: {s.name}\\nTickers: {', '.join(tickers)}\\n")
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
    print(f"\\n  {len(placed)} order(s) placed." if placed else "\\n  No orders placed.")
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
    print(f"\\n  {len(placed)} order(s) placed." if placed else "\\n  No rebalance needed.")
def interactive_menu():
    print("\\n" + "="*50 + "\\n  ALPACA PAPER TRADING BOT\\n" + "="*50)
    tickers = config.DEFAULT_TICKERS
    while True:
        print("\\n1. Status  2. MA Strategy  3. RSI Strategy  4. Rebalance  5. Tickers  6. Dry-run  0. Exit")
        c = input("\\nSelect: ").strip()
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
""",
"scheduler.py": """#!/usr/bin/env python3
import argparse, logging, os, time
from datetime import date, timedelta
import pytz, schedule
import config
from bot import run_strategy, show_status
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
STATE_FILE = os.path.join(os.path.dirname(__file__), ".campaign_start")
def get_start():
    if os.path.exists(STATE_FILE):
        return date.fromisoformat(open(STATE_FILE).read().strip())
    d = date.today()
    open(STATE_FILE,"w").write(d.isoformat())
    log.info(f"Campaign started: {d} (ends {d+timedelta(days=config.CAMPAIGN_DAYS)})")
    return d
def active(s): return (date.today()-s).days < config.CAMPAIGN_DAYS
def job(strategy, dry_run):
    s = get_start()
    if not active(s): log.info("Campaign complete."); return schedule.CancelJob
    log.info(f"Day {(date.today()-s).days+1}/{config.CAMPAIGN_DAYS}")
    show_status()
    for strat in (["ma","rsi","rebalance"] if strategy=="all" else [strategy]):
        run_strategy(strat, config.DEFAULT_TICKERS, dry_run=dry_run)
    log.info("Done.")
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", choices=["ma","rsi","rebalance","all"], default="all")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--now", action="store_true")
    args = p.parse_args()
    s = get_start()
    if not active(s): log.info("Campaign complete. Delete .campaign_start to restart."); return
    log.info(f"Scheduler started. Ends: {s+timedelta(days=config.CAMPAIGN_DAYS)}")
    log.info("Fires at 09:31 ET daily.")
    if args.now: job(args.strategy, args.dry_run)
    schedule.every().day.at("09:31").do(lambda: job(args.strategy, args.dry_run))
    while active(get_start()):
        schedule.run_pending(); time.sleep(30)
    log.info("Campaign complete. Exiting.")
if __name__ == "__main__":
    main()
""",
}

os.makedirs("utils", exist_ok=True)
os.makedirs("strategies", exist_ok=True)

for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)
    print(f"Created: {path}")

print("\nAll files created! Now run: py -m pip install -r requirements.txt")