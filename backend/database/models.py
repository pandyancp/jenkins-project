"""
SQLAlchemy Database Models
==========================
Defines database schemas for stocks, scans, paper trading orders, and backtest logs.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from backend.database.connection import Base, engine


class StockModel(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False)
    market_cap_cr = Column(Float, default=0.0)
    pe_ratio = Column(Float, default=0.0)
    pb_ratio = Column(Float, default=0.0)
    roe_pct = Column(Float, default=0.0)
    roce_pct = Column(Float, default=0.0)
    debt_to_equity = Column(Float, default=0.0)
    avg_daily_volume = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class ScanResultModel(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    price = Column(Float, nullable=False)
    change_pct = Column(Float, default=0.0)
    ema9 = Column(Float, default=0.0)
    ema21 = Column(Float, default=0.0)
    rsi = Column(Float, default=0.0)
    vwap = Column(Float, default=0.0)
    volume = Column(Integer, default=0)
    avg_volume = Column(Integer, default=0)
    tech_score = Column(Float, default=0.0)
    fund_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    signal = Column(String(20), nullable=False)  # BUY SETUP, WATCH, NO TRADE, EXIT
    entry_price = Column(Float, default=0.0)
    stop_loss = Column(Float, default=0.0)
    target = Column(Float, default=0.0)
    position_size = Column(Integer, default=0)


class PaperOrderModel(Base):
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, index=True, nullable=False)
    symbol = Column(String(20), index=True, nullable=False)
    side = Column(String(10), nullable=False)  # BUY or SELL
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")  # OPEN, TARGET_HIT, SL_HIT, CLOSED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")


class BacktestRecordModel(Base):
    __tablename__ = "backtest_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20), nullable=False)
    strategy_name = Column(String(50), default="EMA9_21_RSI")
    timeframe = Column(String(10), default="5m")
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    initial_capital = Column(Float, default=50000.0)
    final_capital = Column(Float, default=50000.0)
    net_pnl = Column(Float, default=0.0)
    net_pnl_pct = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate_pct = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    avg_trade_pnl = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)


# Create tables automatically
Base.metadata.create_all(bind=engine)
