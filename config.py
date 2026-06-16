import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
if not API_KEY or not SECRET_KEY:
    raise EnvironmentError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in .env")

# ---------------------------------------------------------------------------
# Ticker universe — focused bull portfolio
# ---------------------------------------------------------------------------
DEFAULT_TICKERS = ["NVDA","AMD","ANET","INTC","AVGO","MSFT","TQQQ","SOXL","GOOGL"]
LEVERAGED_TICKERS = ["TQQQ","SOXL"]
DEFENSIVE_TICKERS = ["GLD","XOM","WMT","BRK.B"]

# ---------------------------------------------------------------------------
# Tier system
# ---------------------------------------------------------------------------
TIER1 = ["NVDA","AMD","ANET","INTC"]
TIER2 = ["AVGO","MSFT","TQQQ","SOXL","GOOGL"]
TIER3 = ["SQQQ"]

# ---------------------------------------------------------------------------
# Leveraged satellite cap — prevents TQQQ/SOXL from dominating the book
# ---------------------------------------------------------------------------
LEVERAGED_SATELLITE_FRACTION = 0.15

# ---------------------------------------------------------------------------
# RSI parameters
# ---------------------------------------------------------------------------
RSI_PERIOD = 14
RSI_OVERSOLD = 50
RSI_OVERBOUGHT = 70

STRONG_OVERSOLD = 35
NORMAL_OVERSOLD = 60
WEAK_OVERSOLD = 68

TIER1_SELL_RSI = 95
TIER2_SELL_RSI = 92
TIER3_SELL_RSI = 90

# ---------------------------------------------------------------------------
# Order sizing — bigger positions, fewer of them
# ---------------------------------------------------------------------------
ORDER_FRACTION_TIER1_STRONG = 0.20
ORDER_FRACTION_TIER1_NORMAL = 0.15
ORDER_FRACTION_TIER2_STRONG = 0.15
ORDER_FRACTION_TIER2_NORMAL = 0.12
ORDER_FRACTION_TIER3 = 0.10
ORDER_FRACTION = 0.10

# ---------------------------------------------------------------------------
# Trailing stops — wide enough to survive normal volatility
# ---------------------------------------------------------------------------
TIER1_TRAILING_STOP = 10.0
TIER2_TRAILING_STOP = 8.0
TIER3_TRAILING_STOP = 8.0
TRAILING_STOP_PCT = 8.0

# ---------------------------------------------------------------------------
# Market regime
# ---------------------------------------------------------------------------
MARKET_REGIME_TICKER = "SPY"
MARKET_REGIME_MA = 50

# ---------------------------------------------------------------------------
# Risk management
# ---------------------------------------------------------------------------
PROFIT_TAKE_PCT = 0.20
MAX_POSITION_PCT = 0.30
MAX_POSITIONS = 6
TIER1_STOP_LOSS = 0.10
TIER2_STOP_LOSS = 0.10
TIER3_STOP_LOSS = 0.12
STOP_LOSS_PCT = 0.10

# ---------------------------------------------------------------------------
# Rotation
# ---------------------------------------------------------------------------
ROTATION_MIN_GAIN = 0.02
ROTATION_CASH_FLOOR = 0.12

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
BUY_WINDOW_START = 9
BUY_WINDOW_END = 15
MA_SHORT_WINDOW = 10
MA_LONG_WINDOW = 30
VOLUME_MA_DAYS = 20
VOLUME_SURGE_MULT = 1.0
SECTOR_ROTATION_DAYS = 5
CAMPAIGN_DAYS = 30
