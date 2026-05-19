import pandas as pd
from strategies.base import BaseStrategy
import config


class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion - Picks and Shovels"
    description = "Tier-based RSI with reversal candle, volume, regime, and gap filters."

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

    def _above_20ma(self, close):
        if len(close) < 20:
            return True
        return float(close.iloc[-1]) > float(close.rolling(20).mean().iloc[-1])

    def _volume_confirmed(self, df):
        if "volume" not in df.columns or len(df) < config.VOLUME_MA_DAYS:
            return True
        avg_vol = df["volume"].rolling(config.VOLUME_MA_DAYS).mean().iloc[-1]
        return float(df["volume"].iloc[-1]) > float(avg_vol)

    def _reversal_candle(self, df):
        """Last bar closed green with volume surge — genuine bounce signal."""
        if len(df) < 2:
            return False
        green = float(df["close"].iloc[-1]) > float(df["open"].iloc[-1])
        if not green:
            return False
        if len(df) < config.VOLUME_MA_DAYS:
            return green
        avg_vol = float(df["volume"].tail(config.VOLUME_MA_DAYS).mean())
        vol_surge = float(df["volume"].iloc[-1]) > avg_vol * config.VOLUME_SURGE_MULT
        return vol_surge

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
        if tier == 2:
            return config.ORDER_FRACTION_TIER2_STRONG if signal == "strong_buy" else config.ORDER_FRACTION_TIER2_NORMAL
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

    def generate_signals(self, bars, regime="bull"):
        signals = {}

        for sym, df in bars.items():
            if df.empty or len(df) < self.period + 1:
                signals[sym] = ("hold", config.ORDER_FRACTION, config.TRAILING_STOP_PCT)
                continue

            close = df["close"].astype(float)
            rsi = self._rsi(close)
            tier = self._get_tier(sym)
            sell_rsi = self._get_sell_rsi(sym)
            trail = self._get_trailing_stop(sym)

            # --- SELL logic (no filters needed) ---
            if rsi > sell_rsi:
                signals[sym] = ("sell", config.ORDER_FRACTION, trail)
                continue

            # --- Bear regime overrides ---
            if regime == "bear":
                if tier == 3 and sym != "SQQQ":
                    signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                    continue
                if sym == "SQQQ":
                    signals[sym] = ("strong_buy", config.ORDER_FRACTION_TIER1_STRONG, config.TIER1_TRAILING_STOP)
                    continue
                # Defensive tickers always eligible in bear market
                if sym not in config.DEFENSIVE_TICKERS and rsi >= config.STRONG_OVERSOLD:
                    signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                    continue

            # --- Gap down: never buy a falling knife ---
            if self._gap_down(df):
                signals[sym] = ("hold", config.ORDER_FRACTION, trail)
                continue

            # --- Reversal candle required for all buys ---
            reversal = self._reversal_candle(df)
            vol_ok = self._volume_confirmed(df)

            if rsi < config.STRONG_OVERSOLD and reversal and vol_ok:
                signals[sym] = ("strong_buy", self._get_order_fraction(sym, "strong_buy"), trail)
            elif rsi < config.NORMAL_OVERSOLD and reversal and vol_ok:
                signals[sym] = ("buy", self._get_order_fraction(sym, "buy"), trail)
            elif rsi < config.WEAK_OVERSOLD and tier in (1, 2) and reversal and vol_ok:
                signals[sym] = ("buy", self._get_order_fraction(sym, "buy"), trail)
            else:
                signals[sym] = ("hold", config.ORDER_FRACTION, trail)

        return signals
