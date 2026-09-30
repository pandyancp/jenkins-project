"""
WebSocket Manager & Endpoints
=============================
Handles real-time streaming of stock prices, indices, and market updates to the frontend.
"""

import asyncio
import json
from typing import List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.core.logger import logger
from backend.app.services.market_data import MarketDataService

ws_router = APIRouter(tags=["WebSocket"])

class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """Broadcast JSON payload to all active clients."""
        if not self.active_connections:
            return

        message = json.dumps(data)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error sending message to client: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()
market_service: MarketDataService | None = None


def set_ws_market_service(service: MarketDataService):
    global market_service
    market_service = service


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for streaming real-time market data."""
    await manager.connect(websocket)
    
    # Send initial snapshot immediately upon connection
    if market_service:
        try:
            initial_data = {
                "type": "SNAPSHOT",
                "summary": market_service.get_market_summary(),
                "watchlist": market_service.get_watchlist(),
                "indices": market_service.get_indices(),
                "health": market_service.get_system_health(),
            }
            await websocket.send_text(json.dumps(initial_data))
        except Exception as e:
            logger.error(f"Failed to send initial snapshot: {e}")

    try:
        while True:
            # Listen for client requests (e.g. ping/pong, subscribe, etc.)
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")

                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

                elif action == "get_candles":
                    symbol = msg.get("symbol", "RELIANCE").upper()
                    timeframe = msg.get("timeframe", "5m")
                    count = int(msg.get("count", 100))
                    if market_service:
                        candles = market_service.get_candles(symbol, timeframe, count)
                        await websocket.send_text(json.dumps({
                            "type": "CANDLES",
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "candles": candles
                        }))

                elif action == "get_summary":
                    if market_service:
                        await websocket.send_text(json.dumps({
                            "type": "SUMMARY",
                            "summary": market_service.get_market_summary()
                        }))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def market_broadcaster_task():
    """Background task that ticks simulated market data and broadcasts updates."""
    while True:
        try:
            if market_service:
                # Advance simulated tick
                market_service.tick()
                
                # Prepare tick payload
                payload = {
                    "type": "MARKET_TICK",
                    "indices": market_service.get_indices(),
                    "watchlist": market_service.get_watchlist(),
                    "summary": market_service.get_market_summary(),
                    "health": market_service.get_system_health(),
                }
                await manager.broadcast(payload)
        except Exception as e:
            logger.error(f"Broadcaster exception: {e}")

        await asyncio.sleep(1.0)
