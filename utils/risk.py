import time
import config
from utils.client import get_trading_client
from utils.market import get_positions
from utils.orders import place_market_order, cancel_open_trailing_stops, place_trailing_stop

def _trail_pct(sym):
    if sym in config.TIER1: return config.TIER1_TRAILING_STOP
    if sym in config.TIER2: return config.TIER2_TRAILING_STOP
    return config.TIER3_TRAILING_STOP

def check_profit_taking():
    positions = get_positions()
    taken = []
    for sym, pos in positions.items():
        unreal_pct = float(pos.unrealized_plpc)
        if unreal_pct >= config.PROFIT_TAKE_PCT:
            qty = float(pos.qty)
            sell_qty = round(qty * 0.5, 6)
            remaining_qty = round(qty - sell_qty, 6)
            if sell_qty > 0:
                cancel_open_trailing_stops(sym)
                time.sleep(1)
                place_market_order(sym, "sell", sell_qty)
                if int(remaining_qty) > 0:
                    try:
                        place_trailing_stop(sym, int(remaining_qty), _trail_pct(sym))
                    except Exception as e:
                        print(f"  Trailing stop re-place skipped for {sym}: {e}")
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

def _stop_loss_pct(sym):
    if sym in config.TIER1: return config.TIER1_STOP_LOSS
    if sym in config.TIER2: return config.TIER2_STOP_LOSS
    if sym in config.TIER3: return config.TIER3_STOP_LOSS
    return config.STOP_LOSS_PCT

def check_stop_losses(dry_run: bool = False) -> list[str]:
    positions = get_positions()
    stopped = []
    for sym, pos in positions.items():
        plpc = float(pos.unrealized_plpc)
        threshold = -_stop_loss_pct(sym)
        if plpc <= threshold:
            qty = float(pos.qty)
            print(f"  STOP LOSS: {sym} down {plpc*100:.1f}% (threshold {threshold*100:.0f}%) — selling {qty} shares")
            if not dry_run:
                cancel_open_trailing_stops(sym)
                time.sleep(1)
                place_market_order(sym, "sell", qty)
            stopped.append(sym)
    return stopped
