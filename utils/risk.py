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
                try:
                    cancel_open_trailing_stops(sym)
                    place_market_order(sym, "sell", sell_qty)
                    if int(remaining_qty) > 0:
                        try:
                            place_trailing_stop(sym, int(remaining_qty), _trail_pct(sym))
                        except Exception as e:
                            print(f"  Trailing stop re-place skipped for {sym}: {e}")
                    taken.append((sym, unreal_pct * 100, sell_qty))
                    print(f"  PROFIT TAKE: {sym} up {unreal_pct*100:.1f}% - sold half ({sell_qty} shares)")
                except Exception as e:
                    print(f"  PROFIT TAKE skipped for {sym}: {e}")
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
                try:
                    cancel_open_trailing_stops(sym)
                    place_market_order(sym, "sell", qty)
                except Exception as e:
                    print(f"  STOP LOSS sell skipped for {sym}: {e}")
            stopped.append(sym)
    return stopped

def rotate_losers_to_cash(positions, signals, cash, portfolio_value, exclude=None):
    rotated = []
    skip = set(exclude or [])

    # Trim to MAX_POSITIONS — sell worst performers first
    if len(positions) > config.MAX_POSITIONS:
        excess_count = len(positions) - config.MAX_POSITIONS
        candidates = sorted(
            [(sym, float(pos.unrealized_plpc), float(pos.market_value))
             for sym, pos in positions.items()
             if sym not in skip
             and signals.get(sym, ("hold",))[0] not in ("buy", "strong_buy")],
            key=lambda x: x[1]
        )
        for sym, plpc, mv in candidates[:excess_count]:
            qty = float(positions[sym].qty)
            print(f"  TRIM: {sym} ({plpc*100:.1f}%) — over {config.MAX_POSITIONS} position limit")
            try:
                cancel_open_trailing_stops(sym)
                place_market_order(sym, "sell", qty)
                cash += mv
                rotated.append(sym)
                skip.add(sym)
            except Exception as e:
                print(f"  TRIM sell skipped for {sym}: {e}")

    # Rotate cash-poor: sell underperformers to fund winners
    if cash < portfolio_value * config.ROTATION_CASH_FLOOR:
        candidates = sorted(
            [(sym, float(pos.unrealized_plpc), float(pos.market_value))
             for sym, pos in positions.items()
             if sym not in skip
             and float(pos.unrealized_plpc) < config.ROTATION_MIN_GAIN
             and signals.get(sym, ("hold",))[0] not in ("buy", "strong_buy")],
            key=lambda x: x[1]
        )
        for sym, plpc, mv in candidates:
            if cash >= portfolio_value * config.ROTATION_CASH_FLOOR:
                break
            qty = float(positions[sym].qty)
            print(f"  ROTATE: {sym} ({plpc*100:.1f}%) → freeing capital for winners")
            try:
                cancel_open_trailing_stops(sym)
                place_market_order(sym, "sell", qty)
                cash += mv
                rotated.append(sym)
            except Exception as e:
                print(f"  ROTATE sell skipped for {sym}: {e}")

    return cash, rotated
