"""
Risk Manager
==============
Manages position sizing, stop-losses, and enforces trading limits
to protect your capital.
"""

import logging
from datetime import datetime, date
from config import (
    MAX_CAPITAL_PER_TRADE, MAX_TOTAL_CAPITAL,
    STOP_LOSS_PERCENT, TARGET_PROFIT_PERCENT,
    MAX_OPEN_POSITIONS, MAX_DAILY_LOSS
)

logger = logging.getLogger("GrowwBot")


class Position:
    """Represents an open trading position."""

    def __init__(self, symbol, side, quantity, entry_price, order_id):
        self.symbol = symbol
        self.side = side  # "BUY" or "SELL"
        self.quantity = quantity
        self.entry_price = entry_price
        self.order_id = order_id
        self.entry_time = datetime.now()
        self.stop_loss = self._calculate_stop_loss()
        self.target = self._calculate_target()
        self.pnl = 0.0
        self.status = "OPEN"

    def _calculate_stop_loss(self):
        """Calculate stop-loss price."""
        if self.side == "BUY":
            return round(self.entry_price * (1 - STOP_LOSS_PERCENT / 100), 2)
        else:
            return round(self.entry_price * (1 + STOP_LOSS_PERCENT / 100), 2)

    def _calculate_target(self):
        """Calculate target price."""
        if self.side == "BUY":
            return round(self.entry_price * (1 + TARGET_PROFIT_PERCENT / 100), 2)
        else:
            return round(self.entry_price * (1 - TARGET_PROFIT_PERCENT / 100), 2)

    def update_pnl(self, current_price):
        """Update P&L based on current price."""
        if self.side == "BUY":
            self.pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.pnl = (self.entry_price - current_price) * self.quantity
        return self.pnl

    def should_exit(self, current_price):
        """
        Check if position should be exited (stop-loss or target hit).
        
        Returns:
            tuple: (should_exit: bool, reason: str)
        """
        if self.side == "BUY":
            if current_price <= self.stop_loss:
                return True, f"STOP LOSS HIT (₹{current_price:.2f} ≤ ₹{self.stop_loss:.2f})"
            if current_price >= self.target:
                return True, f"TARGET HIT (₹{current_price:.2f} ≥ ₹{self.target:.2f})"
        else:
            if current_price >= self.stop_loss:
                return True, f"STOP LOSS HIT (₹{current_price:.2f} ≥ ₹{self.stop_loss:.2f})"
            if current_price <= self.target:
                return True, f"TARGET HIT (₹{current_price:.2f} ≤ ₹{self.target:.2f})"

        return False, ""

    def to_dict(self):
        """Convert position to dictionary for display."""
        return {
            "Symbol": self.symbol,
            "Side": self.side,
            "Qty": self.quantity,
            "Entry": f"₹{self.entry_price:.2f}",
            "SL": f"₹{self.stop_loss:.2f}",
            "Target": f"₹{self.target:.2f}",
            "P&L": f"₹{self.pnl:+.2f}",
            "Status": self.status,
        }


class RiskManager:
    """
    Enforces risk management rules:
    - Position sizing based on capital limits
    - Stop-loss and take-profit monitoring
    - Maximum position limits
    - Daily loss limits
    """

    def __init__(self):
        self.positions = {}         # symbol -> Position
        self.closed_positions = []  # History of closed positions
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.trade_date = date.today()
        self.capital_used = 0.0
        self.trade_count = 0

    def _reset_daily_if_needed(self):
        """Reset daily counters if it's a new day."""
        if date.today() != self.trade_date:
            logger.info(f"📅 New trading day! Previous day P&L: ₹{self.daily_pnl:+.2f}")
            self.daily_pnl = 0.0
            self.trade_date = date.today()

    def can_trade(self, symbol):
        """
        Check if a new trade is allowed based on risk rules.
        
        Returns:
            tuple: (allowed: bool, reason: str)
        """
        self._reset_daily_if_needed()

        # Check if already in a position for this symbol
        if symbol in self.positions:
            return False, f"Already in position for {symbol}"

        # Check max open positions
        if len(self.positions) >= MAX_OPEN_POSITIONS:
            return False, f"Max positions reached ({MAX_OPEN_POSITIONS})"

        # Check daily loss limit
        if self.daily_pnl <= -MAX_DAILY_LOSS:
            return False, f"Daily loss limit hit (₹{self.daily_pnl:+.2f})"

        # Check capital limit
        if self.capital_used >= MAX_TOTAL_CAPITAL:
            return False, f"Capital limit reached (₹{self.capital_used:.2f} / ₹{MAX_TOTAL_CAPITAL:.2f})"

        return True, "OK"

    def calculate_quantity(self, price):
        """
        Calculate position size based on capital per trade limit.
        
        Args:
            price: Current stock price
            
        Returns:
            int: Number of shares to buy/sell
        """
        if price <= 0:
            return 0

        available_capital = min(
            MAX_CAPITAL_PER_TRADE,
            MAX_TOTAL_CAPITAL - self.capital_used
        )

        quantity = int(available_capital / price)
        return max(quantity, 0)

    def open_position(self, symbol, side, quantity, entry_price, order_id):
        """Record a new open position."""
        position = Position(symbol, side, quantity, entry_price, order_id)
        self.positions[symbol] = position
        self.capital_used += quantity * entry_price
        self.trade_count += 1

        logger.info(
            f"📊 Position opened: {side} {quantity}x {symbol} "
            f"@ ₹{entry_price:.2f} | SL: ₹{position.stop_loss:.2f} | "
            f"Target: ₹{position.target:.2f}"
        )
        return position

    def close_position(self, symbol, exit_price, reason="MANUAL"):
        """Close an existing position and calculate P&L."""
        if symbol not in self.positions:
            logger.warning(f"⚠️ No open position for {symbol}")
            return None

        position = self.positions[symbol]
        position.update_pnl(exit_price)
        position.status = f"CLOSED ({reason})"

        self.daily_pnl += position.pnl
        self.total_pnl += position.pnl
        self.capital_used -= position.quantity * position.entry_price
        self.closed_positions.append(position)
        del self.positions[symbol]

        emoji = "✅" if position.pnl >= 0 else "❌"
        logger.info(
            f"{emoji} Position closed: {symbol} | Reason: {reason} | "
            f"P&L: ₹{position.pnl:+.2f} | Daily P&L: ₹{self.daily_pnl:+.2f}"
        )
        return position

    def check_stop_losses(self, quotes):
        """
        Check all open positions for stop-loss/target hits.
        
        Args:
            quotes: dict of {symbol: current_price}
            
        Returns:
            list of symbols that need to be exited
        """
        exits = []
        for symbol, position in list(self.positions.items()):
            if symbol in quotes:
                current_price = quotes[symbol]
                position.update_pnl(current_price)
                should_exit, reason = position.should_exit(current_price)
                if should_exit:
                    exits.append((symbol, reason))

        return exits

    def get_summary(self):
        """Get a summary of current risk state."""
        return {
            "open_positions": len(self.positions),
            "max_positions": MAX_OPEN_POSITIONS,
            "capital_used": f"₹{self.capital_used:,.2f}",
            "capital_available": f"₹{MAX_TOTAL_CAPITAL - self.capital_used:,.2f}",
            "daily_pnl": f"₹{self.daily_pnl:+,.2f}",
            "total_pnl": f"₹{self.total_pnl:+,.2f}",
            "total_trades": self.trade_count,
            "daily_loss_limit": f"₹{MAX_DAILY_LOSS:,.2f}",
            "trading_allowed": self.daily_pnl > -MAX_DAILY_LOSS,
        }
