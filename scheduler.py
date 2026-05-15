#!/usr/bin/env python3
import argparse, logging, os, time
from datetime import date, timedelta
import pytz, schedule
import config
from bot import run_strategy, show_status
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)
STATE_FILE = os.path.join(os.path.dirname(__file__), ".campaign_start")
def get_start():
    if os.path.exists(STATE_FILE):
        return date.fromisoformat(open(STATE_FILE).read().strip())
    d = date.today()
    open(STATE_FILE,"w").write(d.isoformat())
    log.info(f"Campaign started: {d} (ends {d+timedelta(days=config.CAMPAIGN_DAYS)})")
    return d
def active(s): return (date.today()-s).days < config.CAMPAIGN_DAYS
def job(strategy, dry_run):
    s = get_start()
    if not active(s): log.info("Campaign complete."); return schedule.CancelJob
    log.info(f"Day {(date.today()-s).days+1}/{config.CAMPAIGN_DAYS}")
    show_status()
    for strat in (["ma","rsi","rebalance"] if strategy=="all" else [strategy]):
        run_strategy(strat, config.DEFAULT_TICKERS, dry_run=dry_run)
    log.info("Done.")
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", choices=["ma","rsi","rebalance","all"], default="all")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--now", action="store_true")
    args = p.parse_args()
    s = get_start()
    if not active(s): log.info("Campaign complete. Delete .campaign_start to restart."); return
    log.info(f"Scheduler started. Ends: {s+timedelta(days=config.CAMPAIGN_DAYS)}")
    log.info("Fires at 09:31 ET daily.")
    if args.now: job(args.strategy, args.dry_run)
    schedule.every().day.at("09:31").do(lambda: job(args.strategy, args.dry_run))
    while active(get_start()):
        schedule.run_pending(); time.sleep(30)
    log.info("Campaign complete. Exiting.")
if __name__ == "__main__":
    main()
