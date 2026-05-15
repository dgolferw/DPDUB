import pandas as pd
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
