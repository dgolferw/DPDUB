import config
from utils.client import get_trading_client
from utils.market import get_positions
from utils.orders import place_market_order

def check_profit_taking():
    positions = get_positions()
    taken = []
    for sym, pos in positions.items():
        unreal_pct = float(pos.unrealized_plpc)
        if unreal_pct >= config.PROFIT_TAKE_PCT:
            qty = float(pos.qty)
            sell_qty = round(qty * 0.5, 6)
            if sell_qty > 0:
                place_market_order(sym, "sell", sell_qty)
                taken.append((sym, unreal_pct * 100, sell_qty))
                print(f"  PROFIT TAKE: {sym} up {unreal_pct*100:.1f}% - sold half ({sell_qty} shares)")
    return taken

def check_concentration(sym, qty, price, portfolio_value):
    position_value = qty * price
    if portfolio_value > 0 and (position_value / portfolio_value) > config.MAX_POSITION_PCT:
        max_value = portfolio_value * config.MAX_POSITION_PCT
        max_qty = max_value / price
        return max(round(max_qty, 6), 0)
    return qty
    

def check_stop_losses(dry_run: bool = False) -> list[str]:
    """Hard stop loss: sell entire position if down >= STOP_LOSS_PCT."""
    positions = get_positions()
    stopped = []
    for sym, pos in positions.items():
        plpc = float(pos.unrealized_plpc)
        if plpc <= -config.STOP_LOSS_PCT:
            qty = float(pos.qty)
            log.info(f"STOP LOSS: {sym} down {plpc*100:.1f}% — selling {qty} shares")
            if not dry_run:
                place_market_order(sym, "sell", qty)
            stopped.append(sym)
    return stopped
