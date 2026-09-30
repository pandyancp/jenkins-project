"""
REST API Routes
================
All HTTP endpoints for the trading platform.
"""

from fastapi import APIRouter, HTTPException, Query
from backend.app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/v1", tags=["Market Data"])

# Market data service instance (injected from main.py)
market: MarketDataService | None = None


def set_market_service(service: MarketDataService):
    """Set the shared market data service instance."""
    global market
    market = service


# ─────────────────────────────────────────────
# MARKET OVERVIEW
# ─────────────────────────────────────────────

@router.get("/market/summary")
async def get_market_summary():
    """Get overall market summary with indices and stats."""
    return market.get_market_summary()


@router.post("/market/practice-mode")
async def toggle_practice_mode(enabled: bool = Query(..., description="Enable or disable 24/7 simulation ticks")):
    """Toggle practice simulation mode when real market is closed."""
    state = market.set_practice_mode(enabled)
    return {"status": "ok", "practice_mode": state, "message": f"Practice mode {'enabled' if state else 'disabled'}"}


@router.post("/market/sync-prices")
async def sync_real_prices():
    """Sync latest official closing prices from NSE."""
    market._sync_real_prices()
    return {"status": "ok", "message": "Synced latest NSE market prices"}


@router.get("/market/indices")
async def get_indices():
    """Get all index values (NIFTY 50, BANK NIFTY, SENSEX)."""
    return market.get_indices()


# ─────────────────────────────────────────────
# STOCK QUOTES
# ─────────────────────────────────────────────

@router.get("/quotes")
async def get_all_quotes():
    """Get quotes for all tracked stocks."""
    return market.get_all_quotes()


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote for a specific symbol."""
    quote = market.get_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    return quote


# ─────────────────────────────────────────────
# WATCHLIST
# ─────────────────────────────────────────────

@router.get("/watchlist")
async def get_watchlist():
    """Get watchlist with current prices."""
    return market.get_watchlist()


@router.post("/watchlist/{symbol}")
async def add_to_watchlist(symbol: str):
    """Add a symbol to the watchlist."""
    if market.add_to_watchlist(symbol.upper()):
        return {"status": "ok", "message": f"{symbol.upper()} added to watchlist"}
    raise HTTPException(
        status_code=400,
        detail=f"Cannot add '{symbol}'. Already in watchlist or invalid symbol.",
    )


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove a symbol from the watchlist."""
    if market.remove_from_watchlist(symbol.upper()):
        return {"status": "ok", "message": f"{symbol.upper()} removed from watchlist"}
    raise HTTPException(
        status_code=400,
        detail=f"'{symbol}' not found in watchlist.",
    )


@router.get("/symbols")
async def get_available_symbols():
    """Get all available symbols with metadata."""
    return market.get_available_symbols()


# ─────────────────────────────────────────────
# CHARTS / CANDLES
# ─────────────────────────────────────────────

@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    timeframe: str = Query(default="5m", description="1m, 5m, 15m, 1h, 1d"),
    count: int = Query(default=100, ge=10, le=500),
):
    """Get historical OHLCV candle data for charting."""
    symbol = symbol.upper()
    quote = market.get_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    candles = market.get_candles(symbol, timeframe, count)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }


# ─────────────────────────────────────────────
# SYSTEM HEALTH
# ─────────────────────────────────────────────

@router.get("/health")
async def get_health():
    """Get system health status."""
    return market.get_system_health()
