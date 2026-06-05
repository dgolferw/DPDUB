import config
from utils.market import get_daily_bars

def get_market_regime():
    bars = get_daily_bars([config.MARKET_REGIME_TICKER], days=config.MARKET_REGIME_MA + 10)
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
