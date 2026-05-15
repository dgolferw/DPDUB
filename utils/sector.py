import config
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
    print("\nSector Performance ({}d):".format(config.SECTOR_ROTATION_DAYS))
    active = list(config.HEDGE_TICKERS)
    for i, (sector, ret) in enumerate(sorted_sectors):
        print(f"  {sector:12s} {ret*100:+.2f}%")
        if i < 3:
            active.extend(sectors[sector])
    return list(set(active))
