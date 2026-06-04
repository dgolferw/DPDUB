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
SPACE_TICKERS = ["RKLB","ASTS","LUNR","KTOS","NOC","LMT","ONDS"]
TECH_TICKERS = ["NVDA","AMD","MSFT","GOOGL","AVGO","QCOM","INTC","PLTR","TSLA","COIN","IONQ","ZETA"]
DATACENTER_TICKERS = ["EQIX","DLR","VRT","SMCI","DELL","HPE","GEO","ANET","BE","VST","NRG"]
HEDGE_TICKERS = ["SQQQ"]
DEFENSIVE_TICKERS = ["GLD","XOM","LLY","WMT","BRK.B"]
QUALITY_TICKERS = ["CTSH","CDW","INTU","ROP","BKNG","REGN"]
LEVERAGED_TICKERS = ["TQQQ","SOXL"]

DEFAULT_TICKERS = SPACE_TICKERS + TECH_TICKERS + DATACENTER_TICKERS + HEDGE_TICKERS + DEFENSIVE_TICKERS + QUALITY_TICKERS + LEVERAGED_TICKERS

# ---------------------------------------------------------------------------
# Tier system
# ---------------------------------------------------------------------------
TIER1 = ["NVDA","AMD","INTC","PLTR","EQIX","VRT","ANET","BE","VST","LLY"]
TIER2 = ["AVGO","SMCI","DLR","NRG","MSFT","XOM","WMT","BRK.B","CTSH","CDW","INTU","ROP","BKNG","REGN","GLD","TQQQ"]
TIER3 = ["RKLB","ASTS","IONQ","LUNR","KTOS","COIN","TSLA","GEO","SQQQ","NOC","LMT","GOOGL","QCOM","DELL","HPE","ONDS","ZETA","SOXL"]

# ---------------------------------------------------------------------------
# RSI parameters
# ---------------------------------------------------------------------------
RSI_PERIOD = 7
RSI_OVERSOLD = 50
RSI_OVERBOUGHT = 70

# Buy thresholds (raised for bull market momentum)
STRONG_OVERSOLD = 35
NORMAL_OVERSOLD = 60
WEAK_OVERSOLD = 68

# Sell thresholds per tier (raised to let winners run)
TIER1_SELL_RSI = 85
TIER2_SELL_RSI = 82
TIER3_SELL_RSI = 78

# ---------------------------------------------------------------------------
# Order sizing
# ---------------------------------------------------------------------------
ORDER_FRACTION_TIER1_STRONG = 0.15
ORDER_FRACTION_TIER1_NORMAL = 0.12
ORDER_FRACTION_TIER2_STRONG = 0.10
ORDER_FRACTION_TIER2_NORMAL = 0.10
ORDER_FRACTION_TIER3 = 0.08
ORDER_FRACTION = 0.07

# ---------------------------------------------------------------------------
# Trailing stops
# ---------------------------------------------------------------------------
TIER1_TRAILING_STOP = 6.0
TIER2_TRAILING_STOP = 4.0
TIER3_TRAILING_STOP = 6.0
TRAILING_STOP_PCT = 4.0

# ---------------------------------------------------------------------------
# Market regime
# ---------------------------------------------------------------------------
MARKET_REGIME_TICKER = "SPY"
MARKET_REGIME_MA = 50

# ---------------------------------------------------------------------------
# Risk management
# ---------------------------------------------------------------------------
PROFIT_TAKE_PCT = 0.12
MAX_POSITION_PCT = 0.22
MAX_POSITIONS = 8
TIER1_STOP_LOSS = 0.08
TIER2_STOP_LOSS = 0.06
TIER3_STOP_LOSS = 0.10
STOP_LOSS_PCT = 0.05  # fallback only

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
