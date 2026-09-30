"""
Broker API Interface Architecture
==================================
Provides a clean, modular abstract interface for broker connectivity.
Default implementation is MockPaperBroker for paper trading.
Can easily be swapped for Zerodha Kite, Angel One, Upstox, Groww, or Dhan.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional
from backend.database.connection import SessionLocal
from backend.database.models import PaperOrderModel
from backend.logger import logger


class BrokerInterface(ABC):
    """Abstract Broker Interface for Indian Equities."""

    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch real-time quote for a symbol."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch currently active positions."""
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: int, order_type: str = "MARKET",
                    stop_loss: float = 0.0, target: float = 0.0) -> Dict[str, Any]:
        """Place an order with optional SL/Target brackets."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        pass

    @abstractmethod
    def get_funds(self) -> Dict[str, float]:
        """Get available funds & margin."""
        pass


class MockPaperBroker(BrokerInterface):
    """
    In-memory and SQLite backed paper trading broker.
    Tracks paper executions, stop losses, targets, and simulated P&L.
    """

    def __init__(self, initial_capital: float = 50000.0):
        self.capital = initial_capital
        self.available_cash = initial_capital
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_trades: List[Dict[str, Any]] = []

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        # Handled by market data service
        return {"symbol": symbol, "status": "paper"}

    def get_positions(self) -> List[Dict[str, Any]]:
        return list(self.open_positions.values())

    def place_order(self, symbol: str, side: str, quantity: int, order_type: str = "MARKET",
                    stop_loss: float = 0.0, target: float = 0.0, current_price: float = 0.0) -> Dict[str, Any]:
        """Simulates placing a paper trading order."""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        cost = round(quantity * current_price, 2)

        if side.upper() == "BUY":
            if cost > self.available_cash:
                return {
                    "success": False,
                    "error": f"Insufficient funds. Required: ₹{cost:.2f}, Available: ₹{self.available_cash:.2f}"
                }

            self.available_cash -= cost
            position = {
                "order_id": order_id,
                "symbol": symbol,
                "side": "BUY",
                "quantity": quantity,
                "entry_price": current_price,
                "current_price": current_price,
                "stop_loss": stop_loss,
                "target": target,
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "created_at": datetime.utcnow().isoformat(),
                "status": "OPEN"
            }
            self.open_positions[symbol] = position

            # Record in SQLite Database
            db = SessionLocal()
            try:
                order_db = PaperOrderModel(
                    order_id=order_id,
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    target=target,
                    status="OPEN",
                    created_at=datetime.utcnow(),
                    notes="Automated paper trade execution"
                )
                db.add(order_db)
                db.commit()
            except Exception as e:
                db.rollback()
            finally:
                db.close()

            return {
                "success": True,
                "order_id": order_id,
                "symbol": symbol,
                "side": "BUY",
                "quantity": quantity,
                "price": current_price,
                "status": "FILLED"
            }

        elif side.upper() == "SELL":
            if symbol in self.open_positions:
                pos = self.open_positions.pop(symbol)
                sell_revenue = round(quantity * current_price, 2)
                entry_cost = round(pos["quantity"] * pos["entry_price"], 2)
                pnl = round(sell_revenue - entry_cost, 2)
                pnl_pct = round((pnl / entry_cost) * 100.0, 2)

                self.available_cash += sell_revenue
                self.capital += pnl

                pos["exit_price"] = current_price
                pos["pnl"] = pnl
                pos["pnl_pct"] = pnl_pct
                pos["status"] = "CLOSED"
                pos["closed_at"] = datetime.utcnow().isoformat()
                self.closed_trades.append(pos)

                # Update in DB
                db = SessionLocal()
                try:
                    order_db = db.query(PaperOrderModel).filter(PaperOrderModel.order_id == pos["order_id"]).first()
                    if order_db:
                        order_db.exit_price = current_price
                        order_db.pnl = pnl
                        order_db.pnl_pct = pnl_pct
                        order_db.status = "CLOSED"
                        order_db.closed_at = datetime.utcnow()
                        db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()

                return {
                    "success": True,
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": "SELL",
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "status": "CLOSED"
                }

        return {"success": False, "error": f"Position for {symbol} not found to exit."}

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_funds(self) -> Dict[str, float]:
        unrealized_pnl = sum(p.get("pnl", 0.0) for p in self.open_positions.values())
        return {
            "total_capital": round(self.capital + unrealized_pnl, 2),
            "available_cash": round(self.available_cash, 2),
            "invested": round(self.capital - self.available_cash, 2),
            "unrealized_pnl": round(unrealized_pnl, 2)
        }
