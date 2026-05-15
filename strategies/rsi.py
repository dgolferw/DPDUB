import pandas as pd
from strategies.base import BaseStrategy
import config
class RSIMeanReversion(BaseStrategy):
    name = "RSI Mean Reversion"
    description = f"Buy when RSI({config.RSI_PERIOD}) < {config.RSI_OVERSOLD}; sell when RSI > {config.RSI_OVERBOUGHT}."
    def __init__(self, tickers, period=config.RSI_PERIOD, oversold=config.RSI_OVERSOLD, overbought=config.RSI_OVERBOUGHT):
        super().__init__(tickers)
        self.period = period; self.oversold = oversold; self.overbought = overbought
    def _rsi(self, close):
        d = close.diff().dropna()
        rs = d.clip(lower=0).rolling(self.period).mean() / (-d.clip(upper=0)).rolling(self.period).mean().replace(0, float("inf"))
        return float((100 - 100/(1+rs)).iloc[-1])
    def generate_signals(self, bars):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.period+1: signals[sym] = "hold"; continue
            rsi = self._rsi(df["close"].astype(float))
            if rsi < self.oversold: signals[sym] = "buy"
            elif rsi > self.overbought: signals[sym] = "sell"
            else: signals[sym] = "hold"
        return signals
