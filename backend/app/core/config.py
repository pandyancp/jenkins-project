"""
Application Configuration
==========================
Loads settings from environment variables / .env file.
All secrets and configurable values go here — never hard-coded.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # d:\Algo


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # ── App ──
    APP_NAME: str = "AlgoTrader Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Trading Mode ──
    TRADING_MODE: str = Field(default="paper", description="paper or live")

    # ── Market ──
    EXCHANGE: str = "NSE"
    MARKET_NAME: str = "Indian Stock Market"
    CURRENCY: str = "INR"

    # ── Capital & Risk ──
    CAPITAL: float = 50000.0
    RISK_PER_TRADE: float = 1.0       # Percentage
    MAX_DAILY_LOSS: float = 2.0       # Percentage
    MAX_TRADES_PER_DAY: int = 3
    STOP_LOSS_PERCENT: float = 1.5
    TARGET_PERCENT: float = 3.0

    # ── Strategy Defaults ──
    EMA_FAST: int = 9
    EMA_SLOW: int = 21
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: int = 70
    RSI_OVERSOLD: int = 30

    # ── Broker (for future use) ──
    BROKER_API_KEY: str = ""
    BROKER_API_SECRET: str = ""
    BROKER_ACCESS_TOKEN: str = ""

    # ── Database (for future phases) ──
    DATABASE_URL: str = "sqlite:///./data/algotrader.db"

    # ── Logging ──
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/algotrader.log"

    # ── WebSocket ──
    WS_UPDATE_INTERVAL: float = 1.0  # Seconds between price updates

    # ── NSE Market Hours (IST) ──
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 15
    MARKET_CLOSE_HOUR: int = 15
    MARKET_CLOSE_MINUTE: int = 30

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton settings instance
settings = Settings()
