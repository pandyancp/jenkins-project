"""
Historical Backtesting Engine
=============================
Simulates the EMA 9/21 + RSI strategy across historical multi-day candle data.
Includes realistic transaction costs (STT, exchange turnover, GST, stamp duty) & slippage.
"""

import math
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from backend.models.schemas import BacktestRequest, BacktestResponse
from backend.services.data_service import MarketDataService
from backend.indicators.technical import attach_all_indicators
from backend.database.connection import SessionLocal
from backend.database.models import BacktestRecordModel


class BacktestEngine:
    def __init__(self, data_service: MarketDataService = None):
        self.data_service = data_service or MarketDataService()

    def run_backtest(self, req: BacktestRequest) -> BacktestResponse:
        """
        Executes an event-driven backtest on historical OHLCV data.
        """
        candles_count = min(req.days * 75, 500)  # 75 5-min bars per trading day
        df = self.data_service.get_historical_candles_df(req.symbol, req.timeframe, candles_count)

        capital = req.initial_capital
        peak_capital = req.initial_capital
        max_drawdown = 0.0

        position = None  # None or dict
        trades_history: List[Dict[str, Any]] = []
        total_charges = 0.0

        for i in range(25, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i - 1]

            price = float(curr['close'])
            ema9 = float(curr['ema9'])
            ema21 = float(curr['ema21'])
            rsi = float(curr['rsi'])
            vwap = float(curr.get('vwap', price))
            volume = float(curr['volume'])
            vol_avg = float(curr.get('vol_avg20', volume))
            ts = curr['timestamp'].isoformat() if hasattr(curr['timestamp'], 'isoformat') else str(curr['timestamp'])

            # ── If in position, check Stop Loss, Target, or Strategy Exit ──
            if position:
                pos_qty = position['quantity']
                entry_p = position['entry_price']
                sl_p = position['stop_loss']
                target_p = position['target']

                exit_reason = None
                exit_price = price

                # 1. Target Hit
                if curr['high'] >= target_p:
                    exit_reason = "TARGET HIT"
                    exit_price = target_p
                # 2. Stop Loss Hit
                elif curr['low'] <= sl_p:
                    exit_reason = "STOP LOSS HIT"
                    exit_price = sl_p
                # 3. Strategy Bearish Exit Cross
                elif ema9 < ema21 and rsi < 40.0:
                    exit_reason = "STRATEGY EXIT SIGNAL"
                    exit_price = price

                if exit_reason:
                    # Apply slippage
                    slippage = exit_price * (req.slippage_pct / 100.0)
                    actual_exit_price = round(exit_price - slippage, 2)

                    gross_pnl = round(pos_qty * (actual_exit_price - entry_p), 2)

                    # Indian Regulatory & Brokerage Charges: Brokerage (₹20) + STT (0.025%) + GST (18%) + Stamp (0.003%)
                    turnover = (pos_qty * entry_p) + (pos_qty * actual_exit_price)
                    trade_charges = round(req.brokerage_per_order * 2 + (turnover * 0.0003), 2)
                    net_pnl = round(gross_pnl - trade_charges, 2)
                    total_charges += trade_charges

                    capital += net_pnl
                    peak_capital = max(peak_capital, capital)
                    drawdown = (peak_capital - capital) / peak_capital * 100.0
                    max_drawdown = max(max_drawdown, drawdown)

                    trades_history.append({
                        "entry_time": position['entry_time'],
                        "exit_time": ts,
                        "symbol": req.symbol,
                        "quantity": pos_qty,
                        "entry_price": entry_p,
                        "exit_price": actual_exit_price,
                        "gross_pnl": gross_pnl,
                        "charges": trade_charges,
                        "net_pnl": net_pnl,
                        "pnl_pct": round((net_pnl / (pos_qty * entry_p)) * 100.0, 2),
                        "exit_reason": exit_reason
                    })
                    position = None

            # ── Check Buy Setup Entry Condition ──
            elif not position:
                is_bullish_cross = (ema9 > ema21) and (float(prev['ema9']) <= float(prev['ema21']) or rsi > 50)
                is_above_vwap = price >= vwap
                is_vol_confirmed = volume >= (vol_avg * 0.8)

                if is_bullish_cross and is_above_vwap and is_vol_confirmed and (rsi >= 50 and rsi <= 68):
                    # Apply slippage to entry
                    slippage = price * (req.slippage_pct / 100.0)
                    entry_price = round(price + slippage, 2)

                    sl_price = round(entry_price * (1.0 - (req.stop_loss_pct / 100.0)), 2)
                    target_price = round(entry_price * (1.0 + (req.target_pct / 100.0)), 2)

                    # Position sizing: Risk Amount / (Entry - SL)
                    risk_per_trade = capital * (req.risk_pct / 100.0)
                    risk_per_share = max(entry_price - sl_price, entry_price * 0.01)
                    qty = max(1, min(int(risk_per_trade / risk_per_share), int(capital / entry_price)))

                    position = {
                        "entry_time": ts,
                        "entry_price": entry_price,
                        "quantity": qty,
                        "stop_loss": sl_price,
                        "target": target_price
                    }

        # ── Compute Performance Summary Metrics ──
        total_trades = len(trades_history)
        winning_trades = [t for t in trades_history if t['net_pnl'] > 0]
        losing_trades = [t for t in trades_history if t['net_pnl'] <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = round((win_count / total_trades) * 100.0, 2) if total_trades > 0 else 0.0

        gross_profits = sum(t['net_pnl'] for t in winning_trades)
        gross_losses = abs(sum(t['net_pnl'] for t in losing_trades))
        profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else (round(gross_profits, 2) if gross_profits > 0 else 0.0)

        net_pnl = round(capital - req.initial_capital, 2)
        net_pnl_pct = round((net_pnl / req.initial_capital) * 100.0, 2)

        avg_trade = round(net_pnl / total_trades, 2) if total_trades > 0 else 0.0
        largest_win = max([t['net_pnl'] for t in winning_trades], default=0.0)
        largest_loss = min([t['net_pnl'] for t in losing_trades], default=0.0)

        # Record backtest log in DB
        db = SessionLocal()
        try:
            record = BacktestRecordModel(
                symbol=req.symbol,
                timeframe=req.timeframe,
                initial_capital=req.initial_capital,
                final_capital=round(capital, 2),
                net_pnl=net_pnl,
                net_pnl_pct=net_pnl_pct,
                total_trades=total_trades,
                winning_trades=win_count,
                losing_trades=loss_count,
                win_rate_pct=win_rate,
                profit_factor=profit_factor,
                max_drawdown_pct=round(max_drawdown, 2),
                avg_trade_pnl=avg_trade,
                largest_win=largest_win,
                largest_loss=largest_loss
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return BacktestResponse(
            symbol=req.symbol,
            timeframe=req.timeframe,
            initial_capital=req.initial_capital,
            final_capital=round(capital, 2),
            net_pnl=net_pnl,
            net_pnl_pct=net_pnl_pct,
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            max_drawdown_pct=round(max_drawdown, 2),
            avg_trade_pnl=avg_trade,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_charges_paid=round(total_charges, 2),
            trades=trades_history[-20:]  # Last 20 detailed trades
        )
