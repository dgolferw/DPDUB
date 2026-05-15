from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from utils.client import get_trading_client
import config
def place_market_order(symbol, side, qty):
    order = MarketOrderRequest(symbol=symbol, qty=round(qty,6), side=OrderSide.BUY if side.lower()=="buy" else OrderSide.SELL, time_in_force=TimeInForce.DAY)
    result = get_trading_client().submit_order(order)
    return {"id": str(result.id), "symbol": symbol, "side": side, "qty": qty, "status": str(result.status)}
def calc_order_qty(cash, price, fraction=config.ORDER_FRACTION):
    return max(round((cash * fraction) / price, 6), 0)
