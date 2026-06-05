import config
from utils.market import get_daily_bars

SECTORS = {
    "tech":       ["NVDA","AMD","MSFT","GOOGL","AVGO","INTC","TQQQ"],
    "datacenter": ["ANET","EQIX","VRT","DLR"],
    "defensive":  ["GLD","XOM","WMT","BRK.B"],
    "hedge":      ["SQQQ"],
}

def get_sector_performance() -> dict[str, float]:
    all_tickers = [t for tickers in SECTORS.values() for t in tickers]
    bars = get_daily_bars(all_tickers, days=config.SECTOR_ROTATION_DAYS + 10)
    perf = {}
    for sector, tickers in SECTORS.items():
        returns = []
        for sym in tickers:
            df = bars.get(sym)
            if df is None or len(df) < config.SECTOR_ROTATION_DAYS + 1:
                continue
            start = float(df["close"].iloc[-(config.SECTOR_ROTATION_DAYS + 1)])
            end = float(df["close"].iloc[-1])
            if start > 0:
                returns.append((end - start) / start)
        perf[sector] = sum(returns) / len(returns) if returns else 0.0
    return perf

def get_active_tickers() -> list[str]:
    perf = get_sector_performance()
    sorted_sectors = sorted(perf.items(), key=lambda x: x[1], reverse=True)
    active = []
    for sector, _ in sorted_sectors[:3]:
        active.extend(SECTORS[sector])
    if "SQQQ" not in active:
        active.append("SQQQ")
    return active
