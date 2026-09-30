"""
Automated Test Suite for Indian Algo Trading Platform
=====================================================
Tests technical indicators, strategy rules, risk engine, position sizing,
scanner pipeline, backtesting engine, broker adapters, paper trading, and notifications.
"""

import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from backend.indicators.technical import (
    calculate_ema,
    calculate_rsi,
    calculate_vwap,
    calculate_atr,
    attach_all_indicators,
)
from backend.strategies.ema_rsi import EmaRsiStrategy
from backend.risk.manager import RiskManager
from backend.models.schemas import RiskParams, StrategyConfig, BacktestRequest, PaperOrderCreate
from backend.scanner.stock_scanner import StockScanner
from backend.backtest.engine import BacktestEngine
from backend.services.broker import MockPaperBroker
from backend.broker.interface import OrderSide, OrderType, OrderStatus
from backend.broker.mock_broker import MockBroker
from backend.broker.groww_adapter import GrowwBrokerAdapter
from backend.paper_trading.engine import PaperTradingEngine
from backend.notifications.alerts import NotificationManager
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. TECHNICAL INDICATORS TESTS ──

def test_ema_calculation():
    """Verify EMA is calculated accurately."""
    prices = pd.Series([100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0, 116.0, 118.0])
    ema9 = calculate_ema(prices, 9)
    assert len(ema9) == len(prices)
    assert ema9.iloc[-1] > ema9.iloc[0]


def test_rsi_calculation():
    """Verify RSI responds to upward and downward price action."""
    # Strong upward trend should have high RSI
    up_prices = pd.Series([100 + i * 2 for i in range(30)], dtype=float)
    rsi_up = calculate_rsi(up_prices, 14)
    assert rsi_up.iloc[-1] > 70.0

    # Strong downward trend should have low RSI
    down_prices = pd.Series([200 - i * 2 for i in range(30)], dtype=float)
    rsi_down = calculate_rsi(down_prices, 14)
    assert rsi_down.iloc[-1] < 30.0


def test_vwap_calculation():
    """Verify VWAP calculation on OHLCV dataframe."""
    df = pd.DataFrame({
        "high": [105.0, 110.0, 115.0],
        "low": [95.0, 100.0, 105.0],
        "close": [100.0, 105.0, 110.0],
        "volume": [1000, 2000, 3000]
    })
    vwap = calculate_vwap(df)
    assert len(vwap) == 3
    assert vwap.iloc[0] == 100.0  # typical price of first bar


def test_atr_calculation():
    """Verify ATR calculation for volatility-based stop loss."""
    df = pd.DataFrame({
        "high": [102.0, 105.0, 104.0, 108.0, 110.0],
        "low": [98.0, 100.0, 101.0, 103.0, 105.0],
        "close": [100.0, 104.0, 102.0, 107.0, 109.0]
    })
    atr = calculate_atr(df, period=3)
    assert len(atr) == 5
    assert atr.iloc[-1] > 0.0


# ── 2. STRATEGY & SIGNAL TESTS ──

def test_strategy_signal_generation():
    """Verify strategy outputs expected signals and transparent scoring."""
    strategy = EmaRsiStrategy()

    # Create bullish dataset
    df = pd.DataFrame({
        "close": [100.0 + i for i in range(30)],
        "high": [101.0 + i for i in range(30)],
        "low": [99.0 + i for i in range(30)],
        "volume": [50000 for _ in range(30)]
    })
    df = attach_all_indicators(df)
    eval_res = strategy.evaluate_latest(df)

    assert "signal" in eval_res
    assert eval_res["signal"] in ["BUY SETUP", "WATCH", "NO TRADE", "EXIT"]
    assert "tech_score" in eval_res
    assert 0.0 <= eval_res["tech_score"] <= 100.0


# ── 3. RISK MANAGEMENT & POSITION SIZING TESTS ──

def test_position_sizing_formula():
    """
    Verify position size formula:
    Quantity = Risk Amount / (Entry Price - Stop Loss Price)
    """
    risk_mgr = RiskManager(RiskParams(capital=50000.0, risk_per_trade_pct=1.0))  # Max risk: ₹500

    entry_price = 1000.0
    stop_loss = 980.0  # Risk per share = ₹20
    # Expected qty = 500 / 20 = 25 shares

    pos_info = risk_mgr.calculate_position_size(entry_price, stop_loss)
    assert pos_info["quantity"] == 25
    assert pos_info["actual_risk"] == 500.0
    assert pos_info["target"] == 1030.0  # 3% target


def test_max_open_positions_limit():
    """Verify risk manager halts trading when open positions max out."""
    risk_mgr = RiskManager(RiskParams(max_open_positions=2))
    risk_mgr.open_positions["RELIANCE"] = {"qty": 10}
    risk_mgr.open_positions["INFY"] = {"qty": 15}

    allowed, msg = risk_mgr.is_trading_allowed()
    assert not allowed
    assert "Maximum open positions" in msg


def test_daily_drawdown_limit():
    """Verify circuit breaker trips when daily loss limit is breached."""
    risk_mgr = RiskManager(RiskParams(capital=50000.0, max_daily_loss_pct=2.0))  # Max loss: -₹1,000
    risk_mgr.daily_realized_pnl = -1200.0

    allowed, msg = risk_mgr.is_trading_allowed()
    assert not allowed
    assert "Daily loss limit hit" in msg


def test_emergency_kill_switch():
    """Verify kill switch immediately blocks orders."""
    risk_mgr = RiskManager()
    risk_mgr.toggle_kill_switch(True)

    allowed, msg = risk_mgr.is_trading_allowed()
    assert not allowed
    assert "Kill Switch" in msg


# ── 4. BACKTESTING ENGINE TESTS ──

def test_backtest_engine_run():
    """Verify backtesting engine executes simulations and returns performance metrics."""
    engine = BacktestEngine()
    req = BacktestRequest(
        symbol="RELIANCE",
        timeframe="5m",
        days=15,
        initial_capital=50000.0,
        risk_pct=1.0,
        stop_loss_pct=1.5,
        target_pct=3.0
    )
    res = engine.run_backtest(req)

    assert res.symbol == "RELIANCE"
    assert res.initial_capital == 50000.0
    assert isinstance(res.net_pnl, float)
    assert 0.0 <= res.win_rate_pct <= 100.0
    assert res.total_trades >= 0
    assert isinstance(res.trades, list)


# ── 5. PAPER TRADING & BROKER INTERFACE TESTS ──

def test_paper_trading_execution():
    """Verify placing paper BUY and SELL orders with fund updates."""
    broker = MockPaperBroker(initial_capital=50000.0)

    # Place BUY order
    buy_res = broker.place_order("SBIN", "BUY", quantity=20, current_price=800.0, stop_loss=788.0, target=824.0)
    assert buy_res["success"] is True
    assert len(broker.open_positions) == 1
    assert broker.available_cash == 50000.0 - 16000.0

    # Place SELL (Exit) order
    sell_res = broker.place_order("SBIN", "SELL", quantity=20, current_price=820.0)
    assert sell_res["success"] is True
    assert sell_res["pnl"] == 400.0  # 20 * (820 - 800)
    assert len(broker.open_positions) == 0
    assert broker.capital == 50400.0


def test_paper_engine_slippage_and_brokerage():
    """Verify PaperTradingEngine accurately calculates Indian taxes, brokerage, and slippage."""
    engine = PaperTradingEngine(initial_capital=50000.0, slippage_pct=0.05)
    assert engine.authenticate() is True

    # Place BUY order
    buy_order = engine.place_order(
        symbol="TCS",
        side=OrderSide.BUY,
        quantity=10,
        price=3400.0
    )
    assert buy_order["status"] == OrderStatus.EXECUTED.value
    assert buy_order["price"] > 3400.0  # Slippage added on BUY
    assert len(engine.get_positions()) == 1

    # Place SELL order
    sell_order = engine.place_order(
        symbol="TCS",
        side=OrderSide.SELL,
        quantity=10,
        price=3450.0
    )
    assert sell_order["status"] == OrderStatus.EXECUTED.value
    assert len(engine.get_positions()) == 0
    assert len(engine.trades) == 1
    assert engine.trades[0]["net_pnl"] > 0


def test_groww_adapter_safety_gate():
    """Verify GrowwBrokerAdapter refuses to trade without credentials and explicit auth."""
    adapter = GrowwBrokerAdapter()
    assert adapter.authenticate() is False

    with pytest.raises(PermissionError):
        adapter.place_order("INFY", OrderSide.BUY, 5, price=1800.0)


# ── 6. NOTIFICATION & ALERTS TESTS ──

def test_notification_payload_formatting():
    """Verify notification formatters construct proper alerts."""
    buy_alert = NotificationManager.format_buy_alert(
        symbol="TCS",
        price=3420.0,
        change_pct=1.12,
        score=90,
        entry=3420.0,
        stop_loss=3385.0,
        target=3490.0,
        risk_amount=350.0,
        breakdown={"EMA": True, "VWAP": True, "RSI": True, "Volume": True}
    )
    assert buy_alert["type"] == "BUY_SETUP"
    assert buy_alert["symbol"] == "TCS"
    assert "₹3420" in buy_alert["message"]

    exit_alert = NotificationManager.format_exit_alert(
        symbol="TCS",
        reason="TARGET_HIT",
        exit_price=3490.0,
        pnl=700.0,
        pnl_pct=2.04
    )
    assert exit_alert["type"] == "EXIT_SIGNAL"
    assert "TARGET_HIT" in exit_alert["message"]


# ── 7. FASTAPI API INTEGRATION TESTS ──

def test_scanner_api_endpoint(client):
    """Verify scanner REST endpoint returns structured response."""
    resp = client.get("/api/v1/scanner/run?max_price=2500")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "scanned_count" in data
    assert data["scanned_count"] > 0
    first = data["results"][0]
    assert "signal" in first
    assert "position_size" in first
    assert "stop_loss" in first


def test_stock_candles_endpoint(client):
    """Verify 5-min candle endpoint with attached indicators."""
    resp = client.get("/api/v1/stock/RELIANCE/candles?timeframe=5m&count=50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert len(data["candles"]) == 50
    assert "ema9" in data["candles"][0]
    assert "rsi" in data["candles"][0]
    assert "vwap" in data["candles"][0]
