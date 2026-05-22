import config
from utils.market import get_bars


SECTORS = {
    "space": config.SPACE_TICKERS,
    "tech": config.TECH_TICKERS,
    "datacenter": config.DATACENTER_TICKERS,
    "defensive": config.DEFENSIVE_TICKERS,
    "hedge": config.HEDGE_TICKERS,
    "quality": config.QUALITY_TICKERS,
}

PRIMARY_SECTORS = ["space", "tech", "datacenter", "quality"]


def get_sector_performance() -> dict[str, float]:
    bars = get_bars(config.DEFAULT_TICKERS, days=config.SECTOR_ROTATION_DAYS + 10)
    perf = {}
    for sector, tickers in SECTORS.items():
        returns = []
        for sym in tickers:
            df = bars.get(sym)
            if df is None or len(df) < 2:
                continue
            start = float(df["close"].iloc[-(config.SECTOR_ROTATION_DAYS + 1)])
            end = float(df["close"].iloc[-1])
            if start > 0:
                returns.append((end - start) / start)
        perf[sector] = sum(returns) / len(returns) if returns else 0.0
    return perf


def get_active_tickers() -> list[str]:
    """Return tickers from top 3 performing sectors.
    Always includes defensive tickers when all primary sectors are negative."""
    perf = get_sector_performance()
    sorted_sectors = sorted(perf.items(), key=lambda x: x[1], reverse=True)

    active = []
    for sector, _ in sorted_sectors[:3]:
        active.extend(SECTORS[sector])

    # Force defensive tickers in when all primary sectors are losing
    primary_all_negative = all(perf.get(s, 0) < 0 for s in PRIMARY_SECTORS)
    if primary_all_negative:
        for sym in config.DEFENSIVE_TICKERS:
            if sym not in active:
                active.append(sym)

    # Always include SQQQ as hedge
    if "SQQQ" not in active:
        active.append("SQQQ")

    return active
