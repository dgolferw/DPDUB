import pandas as pd
from strategies.base import BaseStrategy
import config

class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion"
    description = "RSI with volume confirmation, momentum filter, gap filter, and dynamic sizing."

    def __init__(self, tickers, period=config.RSI_PERIOD):
        super().__init__(tickers)
        self.period = period

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

    def generate_signals(self, bars):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.period + 1:
                signals[sym] = ("hold", config.ORDER_FRACTION)
                continue
            close = df["close"].astype(float)
            rsi = self._rsi(close)
            above_ma = self._above_20ma(close)
            vol_ok = self._volume_confirmed(df)
            gap = self._gap_down(df)
            if gap:
                signals[sym] = ("hold", config.ORDER_FRACTION)
            elif rsi < config.STRONG_OVERSOLD and vol_ok:
                signals[sym] = ("strong_buy", config.ORDER_FRACTION_STRONG)
            elif rsi < config.NORMAL_OVERSOLD and above_ma and vol_ok:
                signals[sym] = ("buy", config.ORDER_FRACTION_NORMAL)
            elif rsi < config.WEAK_OVERSOLD and above_ma and vol_ok:
                signals[sym] = ("buy", config.ORDER_FRACTION_WEAK)
            elif rsi > config.RSI_OVERBOUGHT:
                signals[sym] = ("sell", config.ORDER_FRACTION)
            else:
                signals[sym] = ("hold", config.ORDER_FRACTION)
        return signals
