"""
Pydantic Data Schemas
=====================
Request and response models for API validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class StockFilterParams(BaseModel):
    min_volume: int = Field(default=50000, description="Minimum 20-day average volume")
    max_price: float = Field(default=2500.0, description="Maximum stock price limit")
    min_market_cap_cr: float = Field(default=2000.0, description="Minimum market cap in Crores")
    max_debt_to_equity: float = Field(default=2.0, description="Max Debt to Equity ratio")
    min_roe: float = Field(default=10.0, description="Minimum ROE percentage")


class StrategyConfig(BaseModel):
    ema_fast: int = Field(default=9, ge=2, le=50)
    ema_slow: int = Field(default=21, ge=5, le=200)
    rsi_period: int = Field(default=14, ge=2, le=50)
    rsi_buy_level: float = Field(default=50.0, ge=30.0, le=80.0)
    rsi_exit_level: float = Field(default=40.0, ge=20.0, le=60.0)
    volume_multiplier: float = Field(default=1.0, ge=0.5, le=5.0)


class RiskParams(BaseModel):
    capital: float = Field(default=50000.0, gt=0)
    risk_per_trade_pct: float = Field(default=1.0, gt=0, le=10.0)
    stop_loss_pct: float = Field(default=1.5, gt=0.1, le=20.0)
    target_pct: float = Field(default=3.0, gt=0.1, le=50.0)
    max_daily_loss_pct: float = Field(default=2.0, gt=0.1, le=20.0)
    max_open_positions: int = Field(default=3, ge=1, le=20)
    max_trades_per_day: int = Field(default=5, ge=1, le=50)


class ScanItemResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    price: float
    change_pct: float
    ema9: float
    ema21: float
    rsi: float
    vwap: float
    volume: int
    avg_volume: int
    tech_score: float
    fund_score: float
    total_score: float
    signal: str  # BUY SETUP, WATCH, NO TRADE, EXIT
    entry_price: float
    stop_loss: float
    target: float
    position_size: int
    risk_amount: float


class ScannerSummaryResponse(BaseModel):
    market_status: str
    is_market_open: bool
    scanned_count: int
    buy_setups_count: int
    watch_count: int
    no_trade_count: int
    timestamp: str
    results: List[ScanItemResponse]


class BacktestRequest(BaseModel):
    symbol: str = "RELIANCE"
    timeframe: str = "5m"
    days: int = 30
    initial_capital: float = 50000.0
    risk_pct: float = 1.0
    stop_loss_pct: float = 1.5
    target_pct: float = 3.0
    brokerage_per_order: float = 20.0  # Discount broker rate
    slippage_pct: float = 0.05         # Realistic 0.05% execution slippage


class BacktestResponse(BaseModel):
    symbol: str
    timeframe: str
    initial_capital: float
    final_capital: float
    net_pnl: float
    net_pnl_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    avg_trade_pnl: float
    largest_win: float
    largest_loss: float
    total_charges_paid: float
    trades: List[Dict[str, Any]]


class PaperOrderCreate(BaseModel):
    symbol: str
    side: str = "BUY"
    quantity: Optional[int] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
