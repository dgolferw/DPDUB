import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
if not API_KEY or not SECRET_KEY:
    raise EnvironmentError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")

# ---------------------------------------------------------------------------
# Ticker universe
# ---------------------------------------------------------------------------
SPACE_TICKERS = ["RKLB","ASTS","LUNR","KTOS","NOC","LMT"]
TECH_TICKERS = ["NVDA","AMD","MSFT","GOOGL","AVGO","QCOM","INTC","PLTR","TSLA","COIN","IONQ"]
DATACENTER_TICKERS = ["EQIX","DLR","VRT","SMCI","DELL","HPE","GEO","ANET","BE","VST","NRG"]
HEDGE_TICKERS = ["SQQQ"]
DEFENSIVE_TICKERS = ["GLD","XOM","LLY","WMT","BRK.B"]
QUALITY_TICKERS = ["CTSH","CDW","INTU","ROP","BKNG","REGN"]

DEFAULT_TICKERS = SPACE_TICKERS + TECH_TICKERS + DATACENTER_TICKERS + HEDGE_TICKERS + DEFENSIVE_TICKERS + QUALITY_TICKERS

# ---------------------------------------------------------------------------
# Tier system
# ---------------------------------------------------------------------------
TIER1 = ["NVDA","EQIX","VRT","ANET","BE","VST","GLD","LLY"]
TIER2 = ["AMD","AVGO","SMCI","DLR","NRG","MSFT","INTC","PLTR","XOM","WMT","BRK.B","CTSH","CDW","INTU","ROP","BKNG","REGN"]
TIER3 = ["RKLB","ASTS","IONQ","LUNR","KTOS","COIN","TSLA","GEO","SQQQ","NOC","LMT","GOOGL","QCOM","DELL","HPE"]

# ---------------------------------------------------------------------------
# RSI parameters
# ---------------------------------------------------------------------------
RSI_PERIOD = 14
RSI_OVERSOLD = 50
RSI_OVERBOUGHT = 70

# Buy thresholds
STRONG_OVERSOLD = 35
NORMAL_OVERSOLD = 50
WEAK_OVERSOLD = 58

# Sell thresholds per tier
TIER1_SELL_RSI = 78
TIER2_SELL_RSI = 73
TIER3_SELL_RSI = 70

# ---------------------------------------------------------------------------
# Order sizing
# ---------------------------------------------------------------------------
ORDER_FRACTION_TIER1_STRONG = 0.12
ORDER_FRACTION_TIER1_NORMAL = 0.10
ORDER_FRACTION_TIER2_STRONG = 0.10
ORDER_FRACTION_TIER2_NORMAL = 0.08
ORDER_FRACTION_TIER3 = 0.06
ORDER_FRACTION = 0.07

# ---------------------------------------------------------------------------
# Trailing stops
# ---------------------------------------------------------------------------
TIER1_TRAILING_STOP = 6.0
TIER2_TRAILING_STOP = 4.0
TIER3_TRAILING_STOP = 3.0
TRAILING_STOP_PCT = 4.0

# ---------------------------------------------------------------------------
# Market regime
# ---------------------------------------------------------------------------
MARKET_REGIME_TICKER = "SPY"
MARKET_REGIME_MA = 50

# ---------------------------------------------------------------------------
# Risk management
# ---------------------------------------------------------------------------
PROFIT_TAKE_PCT = 0.15
MAX_POSITION_PCT = 0.15
TIER1_STOP_LOSS = 0.08
TIER2_STOP_LOSS = 0.06
TIER3_STOP_LOSS = 0.10
STOP_LOSS_PCT = 0.05  # fallback only

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
BUY_WINDOW_START = 9
BUY_WINDOW_END = 15
MA_SHORT_WINDOW = 10
MA_LONG_WINDOW = 30
VOLUME_MA_DAYS = 20
VOLUME_SURGE_MULT = 1.2
SECTOR_ROTATION_DAYS = 5
CAMPAIGN_DAYS = 30
