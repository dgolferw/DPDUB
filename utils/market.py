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
    """Hourly bars — responsive to intraday price moves for RSI signals."""
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
            rows = [{"open": float(b.open), "high": float(b.high), "low": float(b.low),
                     "close": float(b.close), "volume": float(b.volume), "timestamp": b.timestamp}
                    for b in bars]
            result[sym] = pd.DataFrame(rows)
        except (KeyError, TypeError):
            result[sym] = pd.DataFrame()
    return result


def get_daily_bars(symbols, days=60):
    """Daily bars — used for regime detection and sector rotation."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
        feed="iex",
    )
    raw = get_data_client().get_stock_bars(request)
    result = {}
    for sym in symbols:
        try:
            bars = raw[sym]
            rows = [{"open": float(b.open), "high": float(b.high), "low": float(b.low),
                     "close": float(b.close), "volume": float(b.volume), "timestamp": b.timestamp}
                    for b in bars]
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
