from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
import config
_trading_client = None
_data_client = None
def get_trading_client():
    global _trading_client
    if _trading_client is None:
        _trading_client = TradingClient(api_key=config.API_KEY, secret_key=config.SECRET_KEY, paper=True)
    return _trading_client
def get_data_client():
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(api_key=config.API_KEY, secret_key=config.SECRET_KEY)
    return _data_client
