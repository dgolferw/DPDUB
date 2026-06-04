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
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Hour,
        start=start,
        end=end,
        feed="iex",
    )
    raw = get_data_client().get_stock_bars(request)
    result = {}
    for sym in symbols:
        try:
            bars = raw[sym]
            rows = []
            for bar in bars:
                rows.append({
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": float(bar.volume),
                    "timestamp": bar.timestamp,
                })
            result[sym] = pd.DataFrame(rows)
        except (KeyError, TypeError):
            result[sym] = pd.DataFrame()
    return result


def get_positions():
    return {p.symbol: p for p in get_trading_client().get_all_positions()}


def get_latest_price(symbol):
    bars = get_bars([symbol], days=5)
    df = bars.get(symbol, pd.DataFrame())
    if df.empty:
        raise ValueError(f"No price data for {symbol}")
    return float(df["close"].iloc[-1])
