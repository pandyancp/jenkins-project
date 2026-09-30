"""
AlgoTrader Pro — Main Application
==================================
Indian Stock Market Algo Trading, Stock Scanner, Backtesting, and Paper Trading API.
"""

import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings, BASE_DIR
from backend.logger import logger
from backend.database.connection import get_db, SessionLocal
from backend.database.models import PaperOrderModel, BacktestRecordModel, ScanResultModel
from backend.models.schemas import (
    StockFilterParams,
    StrategyConfig,
    RiskParams,
    ScanItemResponse,
    ScannerSummaryResponse,
    BacktestRequest,
    BacktestResponse,
    PaperOrderCreate,
)
from backend.services.data_service import MarketDataService, NSE_UNIVERSE
from backend.services.broker import MockPaperBroker
from backend.scanner.stock_scanner import StockScanner
from backend.backtest.engine import BacktestEngine
from backend.risk.manager import RiskManager
from backend.api.websocket import ws_router, manager

# Core Singletons
data_service = MarketDataService()
scanner = StockScanner(data_service)
backtest_engine = BacktestEngine(data_service)
paper_broker = MockPaperBroker(initial_capital=settings.INITIAL_CAPITAL)
risk_params = RiskParams(
    capital=settings.INITIAL_CAPITAL,
    risk_per_trade_pct=settings.RISK_PER_TRADE_PCT,
    stop_loss_pct=settings.STOP_LOSS_PCT,
    target_pct=settings.TARGET_PCT,
    max_daily_loss_pct=settings.MAX_DAILY_LOSS_PCT,
    max_open_positions=settings.MAX_OPEN_POSITIONS,
    max_trades_per_day=settings.MAX_TRADES_PER_DAY,
)
risk_manager = RiskManager(params=risk_params)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Mode: {settings.TRADING_MODE.upper()} TRADING | Universe: {len(NSE_UNIVERSE)} NSE Equities (< ₹2,500)")
    yield
    logger.info("Shutting down AlgoTrader Pro.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated Indian Stock Market Scanner, Backtest & Paper Trading Engine",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Frontend Static Assets
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

# Include WebSocket
app.include_router(ws_router)


# ─────────────────────────────────────────────
# 1. SCANNER ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/api/v1/scanner/run", response_model=ScannerSummaryResponse, tags=["Scanner"])
async def run_scanner(
    max_price: float = Query(default=2500.0, description="Max stock price"),
    min_volume: int = Query(default=50000, description="Min avg daily volume"),
    min_roe: float = Query(default=8.0, description="Min ROE %"),
    max_debt_equity: float = Query(default=2.0, description="Max Debt to Equity"),
    ema_fast: int = Query(default=9),
    ema_slow: int = Query(default=21),
    rsi_buy_level: float = Query(default=50.0),
    capital: float = Query(default=50000.0),
    risk_pct: float = Query(default=1.0),
):
    """
    Scans all NSE stocks and produces BUY SETUP, WATCH, and NO TRADE signals with exact sizing.
    """
    filters = StockFilterParams(
        max_price=max_price,
        min_volume=min_volume,
        min_roe=min_roe,
        max_debt_to_equity=max_debt_equity
    )
    strat = StrategyConfig(
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        rsi_buy_level=rsi_buy_level
    )
    risk = RiskParams(
        capital=capital,
        risk_per_trade_pct=risk_pct
    )
    return scanner.scan_all(filters, strat, risk)


# ─────────────────────────────────────────────
# 2. STOCK DETAIL & CANDLES
# ─────────────────────────────────────────────

@app.get("/api/v1/stock/{symbol}/candles", tags=["Stock Details"])
async def get_stock_candles(symbol: str, timeframe: str = "5m", count: int = 150):
    """Get 5-minute candles with EMA 9/21, RSI 14, VWAP and Volume."""
    symbol = symbol.upper()
    df = data_service.get_historical_candles_df(symbol, timeframe, count)
    
    candles = []
    for _, row in df.iterrows():
        ts = row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp'])
        candles.append({
            "time": ts,
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close']),
            "volume": int(row['volume']),
            "ema9": round(float(row['ema9']), 2),
            "ema21": round(float(row['ema21']), 2),
            "rsi": round(float(row['rsi']), 2),
            "vwap": round(float(row.get('vwap', row['close'])), 2),
        })

    fundamentals = data_service.get_stock_fundamentals(symbol)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "fundamentals": fundamentals,
        "candles": candles
    }


# ─────────────────────────────────────────────
# 3. BACKTESTING ENDPOINTS
# ─────────────────────────────────────────────

@app.post("/api/v1/backtest/run", response_model=BacktestResponse, tags=["Backtesting"])
async def run_backtest(req: BacktestRequest):
    """Execute backtest on historical OHLCV data with slippage & taxes."""
    return backtest_engine.run_backtest(req)


@app.get("/api/v1/backtest/history", tags=["Backtesting"])
async def get_backtest_history(db: Session = Depends(get_db)):
    """Get past backtest simulations."""
    records = db.query(BacktestRecordModel).order_by(BacktestRecordModel.id.desc()).limit(20).all()
    return records


# ─────────────────────────────────────────────
# 4. PAPER TRADING & ORDERS
# ─────────────────────────────────────────────

@app.get("/api/v1/orders", tags=["Paper Trading"])
async def get_paper_orders(db: Session = Depends(get_db)):
    """Fetch all open and closed paper trading orders."""
    orders = db.query(PaperOrderModel).order_by(PaperOrderModel.id.desc()).all()
    funds = paper_broker.get_funds()
    return {
        "funds": funds,
        "open_positions": paper_broker.get_positions(),
        "order_history": orders
    }


@app.post("/api/v1/orders", tags=["Paper Trading"])
async def place_paper_order(order: PaperOrderCreate):
    """Place a paper trading order with risk sizing check."""
    # Check risk rules
    allowed, msg = risk_manager.is_trading_allowed()
    if not allowed:
        raise HTTPException(status_code=400, detail=msg)

    # Get latest price
    df = data_service.get_historical_candles_df(order.symbol, "5m", 10)
    current_price = float(df.iloc[-1]['close'])

    pos_info = risk_manager.calculate_position_size(current_price, order.stop_loss)
    qty = order.quantity or pos_info["quantity"]
    sl = order.stop_loss or pos_info["stop_loss"]
    tgt = order.target or pos_info["target"]

    result = paper_broker.place_order(
        symbol=order.symbol.upper(),
        side=order.side.upper(),
        quantity=qty,
        stop_loss=sl,
        target=tgt,
        current_price=current_price
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Order failed"))

    return result


@app.post("/api/v1/orders/{symbol}/exit", tags=["Paper Trading"])
async def exit_paper_position(symbol: str):
    """Exit an open position at current market price."""
    df = data_service.get_historical_candles_df(symbol, "5m", 10)
    current_price = float(df.iloc[-1]['close'])
    
    pos = paper_broker.open_positions.get(symbol.upper())
    if not pos:
        raise HTTPException(status_code=404, detail=f"No active position for {symbol}")

    result = paper_broker.place_order(
        symbol=symbol.upper(),
        side="SELL",
        quantity=pos["quantity"],
        current_price=current_price
    )
    if result.get("success"):
        risk_manager.record_trade_exit(result.get("pnl", 0.0))
    return result


# ─────────────────────────────────────────────
# 5. RISK MANAGEMENT & KILL SWITCH
# ─────────────────────────────────────────────

@app.get("/api/v1/risk/status", tags=["Risk Management"])
async def get_risk_status():
    """Get current risk parameters and drawdown status."""
    return {
        "kill_switch_active": risk_manager.kill_switch_active,
        "daily_realized_pnl": risk_manager.daily_realized_pnl,
        "daily_trades_count": risk_manager.daily_trade_count,
        "current_capital": risk_manager.current_capital,
        "open_positions_count": len(paper_broker.open_positions),
        "params": risk_manager.params
    }


@app.post("/api/v1/risk/kill-switch", tags=["Risk Management"])
async def toggle_kill_switch(active: bool = Query(...)):
    """Emergency toggle to immediately block all new trade executions."""
    state = risk_manager.toggle_kill_switch(active)
    return {"kill_switch_active": state, "message": f"Kill switch {'ACTIVATED' if state else 'DEACTIVATED'}"}


@app.get("/api/v1/system/status", tags=["System"])
async def get_system_status():
    """Get system mode, broker connection status, and active risk limits."""
    mode = settings.TRADING_MODE.upper()
    has_credentials = bool(settings.BROKER_API_KEY and settings.BROKER_API_SECRET)
    return {
        "trading_mode": mode,
        "is_live": mode == "LIVE",
        "broker": "Groww" if has_credentials else "Mock / Paper",
        "broker_connected": has_credentials,
        "capital": settings.INITIAL_CAPITAL,
        "risk_per_trade_pct": settings.RISK_PER_TRADE_PCT,
        "max_daily_loss_pct": settings.MAX_DAILY_LOSS_PCT,
        "max_trades_per_day": settings.MAX_TRADES_PER_DAY,
        "kill_switch_active": risk_manager.kill_switch_active,
    }


# ─────────────────────────────────────────────
# 6. DASHBOARD SPA SERVING
# ─────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    index_file = BASE_DIR / "frontend" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AlgoTrader Pro Backend is running. Frontend located in /frontend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
