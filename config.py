"""
Groww Trading Bot - Indian Market Configuration
=================================================
Configured exclusively for NSE/BSE Indian stock market.

How to get credentials:
1. Log in to groww.in
2. Go to Profile → Settings → Trading APIs
3. Subscribe to API plan (₹499/month)
4. Generate API Key and Secret
5. Set up TOTP for automated login
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# ============================================================
# GROWW API CREDENTIALS (Loaded from .env with fallbacks)
# ============================================================
GROWW_API_KEY = os.getenv("BROKER_API_KEY") or os.getenv("GROWW_API_KEY", "")
GROWW_API_SECRET = os.getenv("BROKER_API_SECRET") or os.getenv("GROWW_API_SECRET", "")
GROWW_ACCESS_TOKEN = os.getenv("BROKER_ACCESS_TOKEN") or os.getenv("GROWW_ACCESS_TOKEN", "")
GROWW_CLIENT_ID = os.getenv("GROWW_CLIENT_ID", "")
GROWW_TOTP_SECRET = os.getenv("GROWW_TOTP_SECRET", "")
GROWW_PASSWORD = os.getenv("GROWW_PASSWORD", "")

# ============================================================
# GROWW API ENDPOINTS
# ============================================================
BASE_URL = os.getenv("GROWW_BASE_URL", "https://growwapi.groww.in")
LOGIN_URL = f"{BASE_URL}/v1/user/login"
ORDER_URL = f"{BASE_URL}/v1/api/order"
POSITION_URL = f"{BASE_URL}/v1/api/position"
HOLDINGS_URL = f"{BASE_URL}/v1/api/holdings"
HISTORICAL_URL = f"{BASE_URL}/v1/api/historical"
MARKET_DATA_URL = f"{BASE_URL}/v1/api/quote"

# ============================================================
# EXCHANGE SETTINGS (INDIA ONLY)
# ============================================================
EXCHANGE = "NSE"           # NSE or BSE
MARKET_NAME = "Indian Stock Market (NSE)"
CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"

# ============================================================
# WATCHLIST - NIFTY 50 TOP STOCKS (Pick your favourites)
# ============================================================

# ── Active Watchlist (Indian stocks below ₹2,500) ──
WATCHLIST = [
    "RELIANCE",     # Reliance Industries (~₹2,450)
    "HDFCBANK",     # HDFC Bank (~₹1,650)
    "INFY",         # Infosys (~₹1,550)
    "ICICIBANK",    # ICICI Bank (~₹1,050)
    "SBIN",         # State Bank of India (~₹780)
    "TATAMOTORS",   # Tata Motors (~₹950)
    "ITC",          # ITC Limited (~₹430)
    "BHARTIARTL",   # Bharti Airtel (~₹1,500)
    "TATASTEEL",    # Tata Steel (~₹145)
    "WIPRO",        # Wipro (~₹450)
]

# ── Sector-wise stocks (All under ₹2,500) ──
NIFTY_IT = ["INFY", "WIPRO", "HCLTECH", "TECHM"]
NIFTY_BANK = ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "PNB"]
NIFTY_PHARMA = ["SUNPHARMA", "CIPLA"]
NIFTY_AUTO = ["TATAMOTORS"]
NIFTY_ENERGY = ["RELIANCE", "NTPC", "POWERGRID", "ONGC", "BPCL", "IOC", "GAIL"]
NIFTY_FMCG = ["HINDUNILVR", "ITC", "NESTLEIND", "TATACONSUM"]
NIFTY_METAL = ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA", "VEDL"]

# ── High Liquidity Indian Stocks Under ₹2,500 ──
STOCKS_UNDER_2500 = [
    "RELIANCE", "NESTLEIND", "HINDUNILVR", "KOTAKBANK", "SUNPHARMA",
    "HDFCBANK", "HCLTECH", "INFY", "BHARTIARTL", "CIPLA",
    "TECHM", "ADANIPORTS", "AXISBANK", "TATACONSUM", "ICICIBANK",
    "TATAMOTORS", "JSWSTEEL", "SBIN", "HINDALCO", "BPCL",
    "COALINDIA", "VEDL", "WIPRO", "ITC", "NTPC",
    "JIOFIN", "POWERGRID", "BEL", "ZOMATO", "ONGC",
    "BHEL", "GAIL", "IOC", "TATASTEEL", "IRFC", "PNB", "NHPC"
]

# ============================================================
# STRATEGY SETTINGS
# ============================================================
STRATEGY = os.getenv("STRATEGY", "SMA_CROSSOVER")  # Options: SMA_CROSSOVER, RSI, MACD, BOLLINGER

# SMA Crossover settings
SMA_FAST_PERIOD = int(os.getenv("EMA_FAST", "9"))       # Fast moving average period
SMA_SLOW_PERIOD = int(os.getenv("EMA_SLOW", "21"))      # Slow moving average period

# RSI settings
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))       # Sell signal
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))           # Buy signal

# MACD settings
MACD_FAST = int(os.getenv("MACD_FAST", "12"))
MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

# Bollinger Bands settings
BB_PERIOD = int(os.getenv("BB_PERIOD", "20"))
BB_STD_DEV = int(os.getenv("BB_STD_DEV", "2"))

# ============================================================
# RISK MANAGEMENT (in ₹ INR)
# ============================================================
MAX_TOTAL_CAPITAL = float(os.getenv("CAPITAL", "500.0"))          # Total capital to deploy
MAX_CAPITAL_PER_TRADE = float(os.getenv("MAX_CAPITAL_PER_TRADE", str(MAX_TOTAL_CAPITAL)))      # Max ₹ per single trade
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "1.5"))            # Stop loss %
TARGET_PROFIT_PERCENT = float(os.getenv("TARGET_PERCENT", os.getenv("TARGET_PROFIT_PERCENT", "3.0")))        # Take profit %
MAX_OPEN_POSITIONS = int(os.getenv("MAX_TRADES_PER_DAY", os.getenv("MAX_OPEN_POSITIONS", "3")))             # Max simultaneous positions
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "2.0"))              # Stop trading if daily loss exceeds limit

# ============================================================
# ORDER SETTINGS (NSE Specific)
# ============================================================
PRODUCT_TYPE = os.getenv("PRODUCT_TYPE", "CNC")       # CNC = Delivery, MIS = Intraday, NRML = F&O
ORDER_VARIETY = os.getenv("ORDER_VARIETY", "REGULAR")  # REGULAR, AMO (After Market Order)
DEFAULT_ORDER_TYPE = os.getenv("DEFAULT_ORDER_TYPE", "MARKET")  # MARKET or LIMIT

# ============================================================
# NSE MARKET TIMING (IST)
# ============================================================
MARKET_OPEN_HOUR = int(os.getenv("MARKET_OPEN_HOUR", "9"))
MARKET_OPEN_MINUTE = int(os.getenv("MARKET_OPEN_MINUTE", "15"))
MARKET_CLOSE_HOUR = int(os.getenv("MARKET_CLOSE_HOUR", "15"))
MARKET_CLOSE_MINUTE = int(os.getenv("MARKET_CLOSE_MINUTE", "30"))
PRE_MARKET_OPEN_HOUR = 9
PRE_MARKET_OPEN_MINUTE = 0
PRE_MARKET_CLOSE_HOUR = 9
PRE_MARKET_CLOSE_MINUTE = 7

CANDLE_INTERVAL = os.getenv("CANDLE_INTERVAL", "5minute")        # Options: 1minute, 5minute, 15minute, 1hour
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))        # How often to check for signals

# ============================================================
# NSE HOLIDAYS 2026 (Market Closed)
# ============================================================
NSE_HOLIDAYS_2026 = [
    "2026-01-26",   # Republic Day
    "2026-03-10",   # Maha Shivaratri
    "2026-03-17",   # Holi
    "2026-03-30",   # Id-Ul-Fitr (Eid)
    "2026-04-02",   # Ram Navami
    "2026-04-03",   # Good Friday
    "2026-04-14",   # Dr. Ambedkar Jayanti
    "2026-05-01",   # Maharashtra Day
    "2026-05-25",   # Buddha Purnima
    "2026-06-06",   # Id-Ul-Adha (Bakri Eid)
    "2026-07-06",   # Muharram
    "2026-08-15",   # Independence Day
    "2026-08-16",   # Parsi New Year
    "2026-09-04",   # Milad-Un-Nabi
    "2026-10-02",   # Mahatma Gandhi Jayanti
    "2026-10-20",   # Dussehra
    "2026-10-22",   # Dussehra (additional)
    "2026-11-09",   # Diwali (Laxmi Puja)
    "2026-11-10",   # Diwali Balipratipada
    "2026-11-30",   # Guru Nanak Jayanti
    "2026-12-25",   # Christmas
]

# ============================================================
# LOGGING
# ============================================================
LOG_FILE = os.getenv("LOG_FILE", "logs/algotrader.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")                 # DEBUG, INFO, WARNING, ERROR

# ============================================================
# MODE
# ============================================================
PAPER_TRADING = os.getenv("TRADING_MODE", "paper").strip().lower() != "live"

