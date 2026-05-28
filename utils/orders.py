import time
from alpaca.trading.requests import MarketOrderRequest, TrailingStopOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus, OrderType
from utils.client import get_trading_client
import config

def place_market_order(symbol, side, qty):
    order = MarketOrderRequest(
        symbol=symbol,
        qty=round(qty, 6),
        side=OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    result = get_trading_client().submit_order(order)
    return {"id": str(result.id), "symbol": symbol, "side": side, "qty": qty, "status": str(result.status)}

def cancel_open_trailing_stops(symbol):
    client = get_trading_client()
    open_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[symbol]))
    cancelled = 0
    for o in open_orders:
        if o.type == OrderType.TRAILING_STOP:
            client.cancel_order_by_id(o.id)
            cancelled += 1
    if cancelled:
        print(f"  Cancelled {cancelled} existing trailing stop(s) for {symbol}")
        for _ in range(6):
            time.sleep(1)
            remaining = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=[symbol]))
            if not any(o.type == OrderType.TRAILING_STOP for o in remaining):
                break

def cancel_orphaned_trailing_stops(position_symbols):
    client = get_trading_client()
    open_orders = client.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN))
    cancelled = 0
    for o in open_orders:
        if o.type == OrderType.TRAILING_STOP and o.symbol not in position_symbols:
            client.cancel_order_by_id(o.id)
            print(f"  Cancelled orphaned trailing stop for {o.symbol} (no position)")
            cancelled += 1
    return cancelled

def place_trailing_stop(symbol, qty, trail_pct=config.TRAILING_STOP_PCT):
    cancel_open_trailing_stops(symbol)
    order = TrailingStopOrderRequest(
        symbol=symbol,
        qty=round(qty, 6),
        side=OrderSide.SELL,
        time_in_force=TimeInForce.GTC,
        trail_percent=trail_pct,
    )
    result = get_trading_client().submit_order(order)
    return {"id": str(result.id), "symbol": symbol, "trail_pct": trail_pct}

def calc_order_qty(cash, price, fraction=config.ORDER_FRACTION):
    return max(round((cash * fraction) / price, 6), 0)
