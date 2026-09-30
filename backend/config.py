"""
Application Configuration
==========================
Centralized configuration loaded from environment variables and .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "AlgoTrader India Scanner & Trading Engine"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Market Configuration
    EXCHANGE: str = Field(default="NSE", validation_alias=AliasChoices("EXCHANGE"))
    CURRENCY: str = Field(default="INR", validation_alias=AliasChoices("CURRENCY"))
    CURRENCY_SYMBOL: str = Field(default="₹", validation_alias=AliasChoices("CURRENCY_SYMBOL"))
    TRADING_MODE: str = Field(default="paper", validation_alias=AliasChoices("TRADING_MODE"))
    PRACTICE_MODE: bool = Field(default=False, validation_alias=AliasChoices("PRACTICE_MODE"))

    # Database
    DATABASE_URL: str = Field(default=f"sqlite:///{BASE_DIR}/data/algotrader.db", validation_alias=AliasChoices("DATABASE_URL"))

    # Risk Management Defaults
    INITIAL_CAPITAL: float = Field(default=50000.0, validation_alias=AliasChoices("INITIAL_CAPITAL", "CAPITAL"))
    RISK_PER_TRADE_PCT: float = Field(default=1.0, validation_alias=AliasChoices("RISK_PER_TRADE_PCT", "RISK_PER_TRADE"))
    MAX_DAILY_LOSS_PCT: float = Field(default=2.0, validation_alias=AliasChoices("MAX_DAILY_LOSS_PCT", "MAX_DAILY_LOSS"))
    STOP_LOSS_PCT: float = Field(default=1.5, validation_alias=AliasChoices("STOP_LOSS_PCT", "STOP_LOSS_PERCENT"))
    TARGET_PCT: float = Field(default=3.0, validation_alias=AliasChoices("TARGET_PCT", "TARGET_PERCENT"))
    MAX_OPEN_POSITIONS: int = Field(default=3, validation_alias=AliasChoices("MAX_OPEN_POSITIONS"))
    MAX_TRADES_PER_DAY: int = Field(default=5, validation_alias=AliasChoices("MAX_TRADES_PER_DAY"))
    KILL_SWITCH_ACTIVE: bool = Field(default=False, validation_alias=AliasChoices("KILL_SWITCH_ACTIVE"))

    # Technical Strategy Defaults
    EMA_FAST_PERIOD: int = Field(default=9, validation_alias=AliasChoices("EMA_FAST_PERIOD", "EMA_FAST"))
    EMA_SLOW_PERIOD: int = Field(default=21, validation_alias=AliasChoices("EMA_SLOW_PERIOD", "EMA_SLOW"))
    RSI_PERIOD: int = Field(default=14, validation_alias=AliasChoices("RSI_PERIOD"))
    RSI_BUY_THRESHOLD: float = Field(default=50.0, validation_alias=AliasChoices("RSI_BUY_THRESHOLD", "RSI_OVERSOLD"))
    RSI_SELL_THRESHOLD: float = Field(default=40.0, validation_alias=AliasChoices("RSI_SELL_THRESHOLD", "RSI_OVERBOUGHT"))
    VOLUME_AVG_PERIOD: int = Field(default=20, validation_alias=AliasChoices("VOLUME_AVG_PERIOD"))

    # Liquidity & Fundamental Scan Filters
    MIN_AVG_VOLUME: int = Field(default=100_000, validation_alias=AliasChoices("MIN_AVG_VOLUME"))
    MAX_PRICE_LIMIT: float = Field(default=2500.0, validation_alias=AliasChoices("MAX_PRICE_LIMIT"))
    MIN_MARKET_CAP_CR: float = Field(default=5000.0, validation_alias=AliasChoices("MIN_MARKET_CAP_CR"))

    # Broker Integration (Mock / Paper by default, or Live if credentials provided)
    BROKER_TYPE: str = Field(default="paper", validation_alias=AliasChoices("BROKER_TYPE", "TRADING_MODE"))
    BROKER_API_KEY: str = Field(default="", validation_alias=AliasChoices("BROKER_API_KEY", "GROWW_API_KEY"))
    BROKER_API_SECRET: str = Field(default="", validation_alias=AliasChoices("BROKER_API_SECRET", "GROWW_API_SECRET"))
    BROKER_ACCESS_TOKEN: str = Field(default="", validation_alias=AliasChoices("BROKER_ACCESS_TOKEN", "GROWW_ACCESS_TOKEN"))

    # Logging
    LOG_LEVEL: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    LOG_FILE: str = Field(default="logs/algotrader.log", validation_alias=AliasChoices("LOG_FILE"))

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


settings = Settings()
