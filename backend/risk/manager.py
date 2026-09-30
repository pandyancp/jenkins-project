"""
Risk Management Engine
======================
Enforces strict capital protection rules for Indian Stock Market trading:
- Position Sizing = Risk Amount / (Entry - Stop Loss)
- Max Open Positions Limit
- Max Daily Loss Circuit Breaker
- Max Daily Trade Count
- Emergency Kill Switch
- Duplicate Order Prevention
"""

from datetime import datetime
from typing import Dict, Any, Tuple
from backend.models.schemas import RiskParams
from backend.config import settings


class RiskManager:
    def __init__(self, params: RiskParams = None):
        self.params = params or RiskParams()
        self.current_capital = self.params.capital
        self.daily_starting_capital = self.params.capital
        self.daily_realized_pnl = 0.0
        self.daily_trade_count = 0
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.kill_switch_active = settings.KILL_SWITCH_ACTIVE
        self.last_reset_date = datetime.now().date()

    def _check_and_reset_daily_stats(self):
        """Resets daily counters on a new trading day."""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_realized_pnl = 0.0
            self.daily_trade_count = 0
            self.daily_starting_capital = self.current_capital
            self.last_reset_date = today

    def is_trading_allowed(self) -> Tuple[bool, str]:
        """
        Comprehensive check before permitting any new order.
        """
        self._check_and_reset_daily_stats()

        # 1. Kill switch
        if self.kill_switch_active:
            return False, "Emergency Kill Switch is ACTIVE. All trading halted."

        # 2. Maximum open positions
        if len(self.open_positions) >= self.params.max_open_positions:
            return False, f"Maximum open positions ({self.params.max_open_positions}) reached."

        # 3. Maximum trades per day
        if self.daily_trade_count >= self.params.max_trades_per_day:
            return False, f"Maximum daily trades ({self.params.max_trades_per_day}) reached for today."

        # 4. Maximum daily drawdown loss limit (Circuit Breaker)
        max_loss_allowed = (self.params.max_daily_loss_pct / 100.0) * self.daily_starting_capital
        if self.daily_realized_pnl <= -max_loss_allowed:
            return False, f"Daily loss limit hit (-₹{abs(self.daily_realized_pnl):.2f} >= max -₹{max_loss_allowed:.2f}). Trading locked."

        return True, "Trading allowed."

    def calculate_position_size(self, entry_price: float, stop_loss_price: float = None) -> Dict[str, Any]:
        """
        Calculates position size strictly using:
        Quantity = Max Risk Amount / (Entry Price - Stop Loss Price)
        """
        if entry_price <= 0:
            return {"quantity": 0, "risk_amount": 0.0, "stop_loss": 0.0, "target": 0.0, "error": "Invalid price"}

        # Calculate SL and Target if not explicitly passed
        if not stop_loss_price or stop_loss_price >= entry_price:
            stop_loss_price = round(entry_price * (1.0 - (self.params.stop_loss_pct / 100.0)), 2)

        target_price = round(entry_price * (1.0 + (self.params.target_pct / 100.0)), 2)

        risk_per_share = entry_price - stop_loss_price
        if risk_per_share <= 0:
            risk_per_share = entry_price * 0.015  # 1.5% fallback

        max_risk_amount = round(self.current_capital * (self.params.risk_per_trade_pct / 100.0), 2)
        calculated_qty = int(max_risk_amount / risk_per_share)

        # Capital ceiling: never exceed total available capital
        max_possible_qty = int(self.current_capital / entry_price)
        final_qty = max(1, min(calculated_qty, max_possible_qty))

        total_exposure = round(final_qty * entry_price, 2)
        actual_risk = round(final_qty * risk_per_share, 2)

        return {
            "quantity": final_qty,
            "entry_price": entry_price,
            "stop_loss": stop_loss_price,
            "target": target_price,
            "risk_per_share": round(risk_per_share, 2),
            "max_risk_amount": max_risk_amount,
            "actual_risk": actual_risk,
            "exposure": total_exposure,
            "risk_reward_ratio": "1:2.0"
        }

    def check_duplicate_order(self, symbol: str) -> bool:
        """Returns True if a position for this symbol is already open."""
        return symbol in self.open_positions

    def record_trade_exit(self, pnl: float):
        """Updates capital and daily P&L when a trade closes."""
        self.daily_realized_pnl += pnl
        self.current_capital += pnl
        self.daily_trade_count += 1

    def toggle_kill_switch(self, active: bool) -> bool:
        """Enables or disables emergency kill switch."""
        self.kill_switch_active = active
        return self.kill_switch_active
