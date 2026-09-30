"""
Broker Interface & Abstract Base Class
======================================
Defines the standard contract for any Indian Broker API adapter
(Zerodha Kite, Groww, AngelOne, Upstox, Dhan, etc.) and Mock/Paper brokers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ProductType(str, Enum):
    INTRADAY = "MIS"      # Margin Intraday Squareoff
    DELIVERY = "CNC"      # Cash and Carry
    NORMAL = "NRML"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class BrokerInterface(ABC):
    """
    Standard Broker Interface for executing orders, retrieving quotes,
    fetching balances, and querying positions across Indian broker APIs.
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate session with the broker using API key / TOTP."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time quote for an NSE symbol."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch list of open positions from broker."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Fetch current status of an order."""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: ProductType = ProductType.INTRADAY,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a buy or sell order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """Fetch current cash balance and margin available."""
        pass
