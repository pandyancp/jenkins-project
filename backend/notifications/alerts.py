"""
Alerts and Notification System
==============================
Formats browser notifications, webhook payloads (Slack/Discord/Telegram),
sound alert events, and email alerts for BUY/SELL signals, risk violations,
and emergency kill-switch activations.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.logger import logger


class NotificationManager:
    """
    Handles distribution and formatting of trading alerts.
    """

    @staticmethod
    def format_buy_alert(
        symbol: str,
        price: float,
        change_pct: float,
        score: int,
        entry: float,
        stop_loss: float,
        target: float,
        risk_amount: float,
        breakdown: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formats a structured BUY SETUP alert.
        """
        payload = {
            "type": "BUY_SETUP",
            "symbol": symbol,
            "title": f"🚨 BUY SETUP: {symbol} (+{change_pct:.2f}%)",
            "message": f"{symbol} crossed criteria with Score {score}/100. Entry: ₹{entry:.2f}, SL: ₹{stop_loss:.2f}, Target: ₹{target:.2f} (Risk: ₹{risk_amount:.2f})",
            "price": price,
            "change_pct": change_pct,
            "score": score,
            "entry": entry,
            "stop_loss": stop_loss,
            "target": target,
            "risk_amount": risk_amount,
            "breakdown": breakdown,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sound": "buy_alert.mp3"
        }
        logger.info(f"[ALERT] BUY SETUP -> {symbol} @ ₹{price:.2f} (Score: {score}/100)")
        return payload

    @staticmethod
    def format_exit_alert(
        symbol: str,
        reason: str,
        exit_price: float,
        pnl: float,
        pnl_pct: float
    ) -> Dict[str, Any]:
        """
        Formats a structured EXIT / SELL alert.
        """
        pnl_sign = "+" if pnl >= 0 else ""
        payload = {
            "type": "EXIT_SIGNAL",
            "symbol": symbol,
            "title": f"🔔 EXIT SIGNAL: {symbol} ({reason})",
            "message": f"Closed {symbol} @ ₹{exit_price:.2f}. Reason: {reason}. P&L: {pnl_sign}₹{pnl:.2f} ({pnl_sign}{pnl_pct:.2f}%)",
            "reason": reason,
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sound": "exit_alert.mp3"
        }
        logger.info(f"[ALERT] EXIT -> {symbol} | Reason: {reason} | P&L: ₹{pnl:.2f}")
        return payload

    @staticmethod
    def format_risk_alert(event_type: str, details: str) -> Dict[str, Any]:
        payload = {
            "type": "RISK_ALERT",
            "title": f"⚠️ RISK ALERT: {event_type}",
            "message": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sound": "warning_alert.mp3"
        }
        logger.warning(f"[RISK ALERT] {event_type} - {details}")
        return payload
