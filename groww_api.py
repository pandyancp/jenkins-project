"""
Groww API Client
=================
Handles authentication, order placement, and market data fetching
from the Groww Trading API.

NOTE: Groww's API is relatively new and documentation may change.
This module provides a structured interface. You may need to adjust
endpoints based on the latest Groww API documentation.
"""

import requests
import pyotp
import logging
import time
import json
from datetime import datetime, timedelta
from config import (
    GROWW_API_KEY, GROWW_API_SECRET, GROWW_CLIENT_ID,
    GROWW_TOTP_SECRET, GROWW_PASSWORD, GROWW_ACCESS_TOKEN, BASE_URL,
    PAPER_TRADING
)

logger = logging.getLogger("GrowwBot")


class GrowwAPIError(Exception):
    """Custom exception for Groww API errors."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class GrowwAPI:
    """
    Client for interacting with the Groww Trading API.
    
    Handles:
    - Authentication with TOTP or direct Access Token
    - Placing buy/sell orders
    - Fetching positions, holdings
    - Getting market quotes and historical data
    """

    def __init__(self):
        self.session = requests.Session()
        self.access_token = GROWW_ACCESS_TOKEN if GROWW_ACCESS_TOKEN else None
        self.token_expiry = datetime.now() + timedelta(hours=24) if self.access_token else None
        self.headers = {
            "Content-Type": "application/json",
            "X-Groww-Api-Key": GROWW_API_KEY,
        }
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        self.session.headers.update(self.headers)

    # ──────────────────────────────────────────────
    # AUTHENTICATION
    # ──────────────────────────────────────────────

    def login(self):
        """
        Authenticate with Groww API using credentials + TOTP.
        Sets access_token for subsequent requests.
        """
        try:
            # Generate TOTP
            totp = pyotp.TOTP(GROWW_TOTP_SECRET)
            otp = totp.now()

            payload = {
                "clientId": GROWW_CLIENT_ID,
                "password": GROWW_PASSWORD,
                "totp": otp,
                "apiKey": GROWW_API_KEY,
                "apiSecret": GROWW_API_SECRET,
            }

            logger.info("🔐 Logging in to Groww API...")
            response = self.session.post(
                f"{BASE_URL}/v1/user/login",
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken") or data.get("token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                self.token_expiry = datetime.now() + timedelta(hours=8)
                logger.info("✅ Login successful!")
                return True
            else:
                raise GrowwAPIError(
                    f"Login failed: {response.text}",
                    status_code=response.status_code,
                    response=response
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error during login: {e}")
            raise GrowwAPIError(f"Network error: {e}")

    def ensure_authenticated(self):
        """Re-authenticate if token is expired or missing."""
        if PAPER_TRADING:
            return  # Skip auth in paper trading mode
        if not self.access_token or (
            self.token_expiry and datetime.now() >= self.token_expiry
        ):
            self.login()

    # ──────────────────────────────────────────────
    # MARKET DATA
    # ──────────────────────────────────────────────

    def get_quote(self, symbol):
        """
        Get real-time quote for a stock.
        
        Args:
            symbol: NSE stock symbol (e.g., "RELIANCE")
            
        Returns:
            dict with price data (ltp, open, high, low, close, volume)
        """
        self.ensure_authenticated()

        if PAPER_TRADING:
            return self._generate_simulated_quote(symbol)

        try:
            response = self.session.get(
                f"{BASE_URL}/v1/api/quote/{symbol}",
                params={"exchange": "NSE"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "symbol": symbol,
                    "ltp": data.get("lastPrice", 0),
                    "open": data.get("open", 0),
                    "high": data.get("high", 0),
                    "low": data.get("low", 0),
                    "close": data.get("close", 0),
                    "volume": data.get("volume", 0),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                logger.warning(f"⚠️ Failed to get quote for {symbol}: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error fetching quote: {e}")
            return None

    def _generate_simulated_quote(self, symbol):
        """
        Generate simulated price data for paper trading.
        Uses random walk to create realistic-looking price movements.
        """
        import random

        # Base prices for Indian stocks below ₹2,500 (approximate ₹ prices)
        base_prices = {
            # ── Large & Mid Cap Indian Equities (< ₹2,500) ──
            "RELIANCE": 2450.0, "NESTLEIND": 2400.0, "HINDUNILVR": 2350.0,
            "KOTAKBANK": 1750.0, "SUNPHARMA": 1700.0, "HDFCBANK": 1650.0,
            "HCLTECH": 1600.0, "INFY": 1550.0, "BHARTIARTL": 1500.0,
            "CIPLA": 1450.0, "TECHM": 1400.0, "ADANIPORTS": 1300.0,
            "AXISBANK": 1100.0, "TATACONSUM": 1100.0, "ICICIBANK": 1050.0,
            "TATAMOTORS": 950.0, "JSWSTEEL": 850.0, "SBIN": 780.0,
            "HINDALCO": 600.0, "BPCL": 580.0, "COALINDIA": 480.0,
            "VEDL": 460.0, "WIPRO": 450.0, "ITC": 430.0,
            "NTPC": 350.0, "JIOFIN": 340.0, "POWERGRID": 310.0,
            "BEL": 285.0, "ZOMATO": 275.0, "ONGC": 260.0,
            "BHEL": 255.0, "GAIL": 215.0, "IOC": 170.0,
            "TATASTEEL": 145.0, "IRFC": 140.0, "PNB": 105.0, "NHPC": 90.0
        }

        base = base_prices.get(symbol, 1000.0)

        # Initialize price tracker if not exists
        if not hasattr(self, '_sim_prices'):
            self._sim_prices = {}
        
        if symbol not in self._sim_prices:
            # Start with slight random offset
            self._sim_prices[symbol] = base * (1 + random.uniform(-0.02, 0.02))

        # Random walk: price moves ±0.1% to ±0.5%
        change_pct = random.gauss(0, 0.003)  # Normal distribution, 0.3% std dev
        self._sim_prices[symbol] *= (1 + change_pct)
        price = round(self._sim_prices[symbol], 2)

        return {
            "symbol": symbol,
            "ltp": price,
            "open": round(price * 0.998, 2),
            "high": round(price * 1.005, 2),
            "low": round(price * 0.995, 2),
            "close": round(price * 0.999, 2),
            "volume": random.randint(100000, 5000000),
            "timestamp": datetime.now().isoformat(),
        }

    def get_historical_data(self, symbol, interval="5minute", days=30):
        """
        Get historical OHLCV data for backtesting/analysis.
        
        Args:
            symbol: NSE stock symbol
            interval: Candle interval (1minute, 5minute, 15minute, 1hour, 1day)
            days: Number of days of history
            
        Returns:
            list of dicts with OHLCV data
        """
        self.ensure_authenticated()

        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")

            response = self.session.get(
                f"{BASE_URL}/v1/api/historical/{symbol}",
                params={
                    "exchange": "NSE",
                    "interval": interval,
                    "from": from_date,
                    "to": to_date,
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                candles = data.get("candles", data.get("data", []))
                logger.info(f"📈 Fetched {len(candles)} candles for {symbol}")
                return candles
            else:
                logger.warning(f"⚠️ Failed to get history for {symbol}: {response.status_code}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error fetching historical data: {e}")
            return []

    # ──────────────────────────────────────────────
    # ORDER MANAGEMENT
    # ──────────────────────────────────────────────

    def place_order(self, symbol, side, quantity, price=None, order_type="MARKET"):
        """
        Place a buy or sell order.
        
        Args:
            symbol: NSE stock symbol
            side: "BUY" or "SELL"
            quantity: Number of shares
            price: Limit price (None for market orders)
            order_type: "MARKET" or "LIMIT"
            
        Returns:
            dict with order_id and status
        """
        self.ensure_authenticated()

        if PAPER_TRADING:
            order_id = f"PAPER-{int(time.time())}"
            logger.info(
                f"📝 [PAPER TRADE] {side} {quantity}x {symbol} "
                f"@ {'MARKET' if not price else f'₹{price}'} | Order ID: {order_id}"
            )
            return {
                "order_id": order_id,
                "status": "SIMULATED",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_type": order_type,
                "timestamp": datetime.now().isoformat(),
            }

        # LIVE ORDER
        payload = {
            "symbol": symbol,
            "exchange": "NSE",
            "transactionType": side,
            "quantity": quantity,
            "orderType": order_type,
            "product": "CNC",  # CNC for delivery, MIS for intraday
            "validity": "DAY",
        }

        if price and order_type == "LIMIT":
            payload["price"] = price

        try:
            logger.info(f"🚀 Placing {side} order: {quantity}x {symbol}")
            response = self.session.post(
                f"{BASE_URL}/v1/api/order/place",
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                order_id = data.get("orderId", data.get("order_id", "UNKNOWN"))
                logger.info(f"✅ Order placed! ID: {order_id}")
                return {
                    "order_id": order_id,
                    "status": data.get("status", "PLACED"),
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "order_type": order_type,
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                raise GrowwAPIError(
                    f"Order failed: {response.text}",
                    status_code=response.status_code
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error placing order: {e}")
            raise GrowwAPIError(f"Network error: {e}")

    def cancel_order(self, order_id):
        """Cancel a pending order."""
        self.ensure_authenticated()

        if PAPER_TRADING:
            logger.info(f"📝 [PAPER] Cancelled order: {order_id}")
            return True

        try:
            response = self.session.delete(
                f"{BASE_URL}/v1/api/order/{order_id}",
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"✅ Order {order_id} cancelled")
                return True
            else:
                logger.warning(f"⚠️ Failed to cancel order {order_id}: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error cancelling order: {e}")
            return False

    def get_order_status(self, order_id):
        """Get status of a specific order."""
        self.ensure_authenticated()

        if PAPER_TRADING:
            return {"order_id": order_id, "status": "COMPLETED"}

        try:
            response = self.session.get(
                f"{BASE_URL}/v1/api/order/{order_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching order status: {e}")
            return None

    # ──────────────────────────────────────────────
    # PORTFOLIO
    # ──────────────────────────────────────────────

    def get_positions(self):
        """Get all open positions."""
        self.ensure_authenticated()

        if PAPER_TRADING:
            return []

        try:
            response = self.session.get(
                f"{BASE_URL}/v1/api/position",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("positions", [])
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching positions: {e}")
            return []

    def get_holdings(self):
        """Get all holdings in the account."""
        self.ensure_authenticated()

        if PAPER_TRADING:
            return []

        try:
            response = self.session.get(
                f"{BASE_URL}/v1/api/holdings",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("holdings", [])
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching holdings: {e}")
            return []

    def get_funds(self):
        """Get available funds/balance."""
        self.ensure_authenticated()

        if PAPER_TRADING:
            from config import MAX_TOTAL_CAPITAL
            return {"available": MAX_TOTAL_CAPITAL, "used": 0}

        try:
            response = self.session.get(
                f"{BASE_URL}/v1/api/funds",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching funds: {e}")
            return None
