from datetime import datetime, timedelta, timezone
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
