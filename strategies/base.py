from abc import ABC, abstractmethod
import pandas as pd
class BaseStrategy(ABC):
    name = "Base"
    description = ""
    def __init__(self, tickers):
        self.tickers = tickers
    @abstractmethod
    def generate_signals(self, bars):
        pass
