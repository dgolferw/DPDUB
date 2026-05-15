import pandas as pd
from strategies.base import BaseStrategy
import config
class MovingAverageCrossover(BaseStrategy):
    name = "Moving Average Crossover"
    description = f"Buy when {config.MA_SHORT_WINDOW}-day MA crosses above {config.MA_LONG_WINDOW}-day MA; sell when it crosses below."
    def __init__(self, tickers, short_window=config.MA_SHORT_WINDOW, long_window=config.MA_LONG_WINDOW):
        super().__init__(tickers)
        self.short_window = short_window
        self.long_window = long_window
    def generate_signals(self, bars):
        signals = {}
        for sym, df in bars.items():
            if df.empty or len(df) < self.long_window:
                signals[sym] = "hold"; continue
            close = df["close"].astype(float)
            s = close.rolling(self.short_window).mean()
            l = close.rolling(self.long_window).mean()
            if s.iloc[-2] <= l.iloc[-2] and s.iloc[-1] > l.iloc[-1]: signals[sym] = "buy"
            elif s.iloc[-2] >= l.iloc[-2] and s.iloc[-1] < l.iloc[-1]: signals[sym] = "sell"
            else: signals[sym] = "hold"
        return signals
