from strategies.base import BaseStrategy
class BuyHoldRebalance(BaseStrategy):
    name = "Buy & Hold Rebalance"
    description = "Maintain equal-weight allocation across tickers."
    def generate_signals(self, bars):
        return {sym: "hold" for sym in self.tickers}
