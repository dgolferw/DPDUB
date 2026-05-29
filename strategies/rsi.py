import pandas as pd
from strategies.base import BaseStrategy
import config


class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion - Picks and Shovels"

    def __init__(self, tickers, period=config.RSI_PERIOD):
        super().__init__(tickers)
        self.period = period

    def _get_tier(self, sym):
        if sym in config.TIER1: return 1
        if sym in config.TIER2: return 2
        return 3

    def _rsi(self, close):
        d = close.diff().dropna()
        rs = d.clip(lower=0).rolling(self.period).mean() / \
             (-d.clip(upper=0)).rolling(self.period).mean().replace(0, float("inf"))
        return float((100 - 100 / (1 + rs)).iloc[-1])

    def _get_order_fraction(self, sym, rsi):
        tier = self._get_tier(sym)
        strong = rsi < config.STRONG_OVERSOLD
        if tier == 1:
            return config.ORDER_FRACTION_TIER1_STRONG if strong else config.ORDER_FRACTION_TIER1_NORMAL
        if tier == 2:
            return config.ORDER_FRACTION_TIER2_STRONG if strong else config.ORDER_FRACTION_TIER2_NORMAL
        return config.ORDER_FRACTION_TIER3

    def _get_sell_rsi(self, sym):
        tier = self._get_tier(sym)
        if tier == 1: return config.TIER1_SELL_RSI
        if tier == 2: return config.TIER2_SELL_RSI
        return config.TIER3_SELL_RSI

    def _get_trailing_stop(self, sym):
        tier = self._get_tier(sym)
        if tier == 1: return config.TIER1_TRAILING_STOP
        if tier == 2: return config.TIER2_TRAILING_STOP
        return config.TIER3_TRAILING_STOP

    def _has_volume(self, df):
        if "volume" not in df.columns or len(df) < config.VOLUME_MA_DAYS:
            return True
        vol_ma = df["volume"].iloc[-config.VOLUME_MA_DAYS:].mean()
        return float(df["volume"].iloc[-1]) >= vol_ma * config.VOLUME_SURGE_MULT

    def generate_signals(self, bars, regime="bull"):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.period + 1:
                signals[sym] = ("hold", config.ORDER_FRACTION, config.TRAILING_STOP_PCT)
                continue

            rsi = self._rsi(df["close"].astype(float))
            tier = self._get_tier(sym)
            trail = self._get_trailing_stop(sym)

            if sym == "SQQQ":
                if regime == "bear":
                    signals[sym] = ("strong_buy", config.ORDER_FRACTION_TIER1_STRONG, config.TIER1_TRAILING_STOP)
                else:
                    signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                continue

            if regime == "bear":
                if tier == 3 and sym not in config.DEFENSIVE_TICKERS:
                    signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                    continue

            has_vol = self._has_volume(df)

            if rsi > self._get_sell_rsi(sym):
                signals[sym] = ("sell", config.ORDER_FRACTION, trail)
            elif rsi < config.STRONG_OVERSOLD and has_vol:
                signals[sym] = ("strong_buy", self._get_order_fraction(sym, rsi), trail)
            elif rsi < config.NORMAL_OVERSOLD and has_vol:
                signals[sym] = ("buy", self._get_order_fraction(sym, rsi), trail)
            elif rsi < config.WEAK_OVERSOLD and has_vol and (tier in (1, 2) or sym in config.DEFENSIVE_TICKERS):
                signals[sym] = ("buy", self._get_order_fraction(sym, rsi), trail)
            elif regime == "bull" and 52 < rsi < 72 and tier in (1, 2) and has_vol:
                signals[sym] = ("buy", config.ORDER_FRACTION_TIER2_NORMAL, trail)
            else:
                signals[sym] = ("hold", config.ORDER_FRACTION, trail)

        return signals
