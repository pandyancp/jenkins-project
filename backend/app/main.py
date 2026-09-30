"""
FastAPI Application Entry Point
===============================
Indian Stock Market Algo Trading Platform - Phase 1 Backend
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.core.config import settings, BASE_DIR
from backend.app.core.logger import logger
from backend.app.services.market_data import MarketDataService
from backend.app.api.routes import router as api_router, set_market_service
from backend.app.api.websocket import (
    ws_router,
    set_ws_market_service,
    market_broadcaster_task,
)

# Shared service instance
market_service = MarketDataService()
set_market_service(market_service)
set_ws_market_service(market_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.TRADING_MODE} mode)")
    
    # Wire market service
    set_market_service(market_service)
    set_ws_market_service(market_service)

    # Start WebSocket broadcaster task
    broadcast_task = asyncio.create_task(market_broadcaster_task())
    logger.info("Market data simulator & WebSocket broadcaster running.")

    yield

    # Shutdown
    logger.info("Shutting down AlgoTrader...")
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    logger.info("AlgoTrader stopped.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Professional Indian Stock Market Algo Trading Platform",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API and WebSocket routers
app.include_router(api_router)
app.include_router(ws_router)

# Mount frontend static assets
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the dashboard frontend single page application."""
    index_file = BASE_DIR / "frontend" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AlgoTrader Pro API is running. Frontend not found at /frontend/index.html"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
