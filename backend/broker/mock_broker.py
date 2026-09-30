"""
Mock Broker Implementation
==========================
Extends BrokerInterface to simulate broker API connectivity, orders,
and portfolio state for testing and development environments.
"""

from typing import Dict, Any, List, Optional
from backend.broker.interface import BrokerInterface, OrderType, OrderSide, ProductType, OrderStatus
from backend.paper_trading.engine import PaperTradingEngine


class MockBroker(PaperTradingEngine):
    """
    Mock Broker implementation conforming to BrokerInterface.
    Uses PaperTradingEngine to simulate simulated execution.
    """
    def __init__(self, initial_capital: float = 50000.0):
        super().__init__(initial_capital=initial_capital)
        self.is_authenticated = True

    def authenticate(self) -> bool:
        self.is_authenticated = True
        return True
