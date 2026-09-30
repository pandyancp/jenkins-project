"""
Phase 1 Automated Tests
=======================
Tests API endpoints, market data service, and simulation math.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, market_service
from backend.app.services.market_data import STOCK_DATABASE


@pytest.fixture
def client():
    return TestClient(app)


def test_market_summary_endpoint(client):
    """Verify market summary returns indices, counts, and status."""
    response = client.get("/api/v1/market/summary")
    assert response.status_code == 200
    data = response.json()
    assert "indices" in data
    assert "NIFTY 50" in data["indices"]
    assert "BANK NIFTY" in data["indices"]
    assert "SENSEX" in data["indices"]
    assert data["total_stocks"] == len(STOCK_DATABASE)


def test_quotes_endpoint(client):
    """Verify all stock quotes."""
    response = client.get("/api/v1/quotes")
    assert response.status_code == 200
    quotes = response.json()
    assert len(quotes) == len(STOCK_DATABASE)
    assert "RELIANCE" in quotes
    assert quotes["RELIANCE"]["symbol"] == "RELIANCE"


def test_watchlist_operations(client):
    """Verify watchlist get, add, and remove operations."""
    # Get initial watchlist
    response = client.get("/api/v1/watchlist")
    assert response.status_code == 200
    watchlist = response.json()
    assert len(watchlist) > 0

    # Add new stock
    response = client.post("/api/v1/watchlist/MARUTI")
    assert response.status_code in [200, 400]  # 400 if already present

    # Remove stock
    response = client.delete("/api/v1/watchlist/MARUTI")
    assert response.status_code in [200, 400]


def test_candles_endpoint(client):
    """Verify OHLCV candlestick generation."""
    response = client.get("/api/v1/candles/RELIANCE?timeframe=5m&count=50")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "RELIANCE"
    assert data["count"] == 50
    assert len(data["candles"]) == 50

    candle = data["candles"][0]
    for key in ["time", "open", "high", "low", "close", "volume"]:
        assert key in candle


def test_health_endpoint(client):
    """Verify system health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["backend"] == "ONLINE"
    assert data["market_data"] in ["LIVE NSE", "NSE CLOSING DATA", "SIMULATED"]
    assert data["trading_mode"] == "PAPER"
