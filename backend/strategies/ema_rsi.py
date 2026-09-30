"""
5-Minute EMA 9/21 + RSI + VWAP Strategy
========================================
Implements rule-based strategy signal evaluation for Indian equities.
Produces signals: BUY SETUP, WATCH, NO TRADE, EXIT
"""

import pandas as pd
from typing import Dict, Any
from backend.models.schemas import StrategyConfig


class EmaRsiStrategy:
    """
    Evaluates intraday conditions on 5-minute candles:
    - EMA Trend: Fast EMA (9) vs Slow EMA (21)
    - Momentum: RSI (14)
    - Institutional Fair Value: VWAP
    - Liquidity Confirmation: Volume vs 20-period average
    """

    def __init__(self, config: StrategyConfig = None):
        self.config = config or StrategyConfig()

    def evaluate_latest(self, df_with_indicators: pd.DataFrame) -> Dict[str, Any]:
        """
        Evaluate signal and compute technical score for the most recent candle.
        """
        if len(df_with_indicators) < 2:
            return {
                "signal": "NO TRADE",
                "tech_score": 0.0,
                "reason": "Insufficient data"
            }

        last = df_with_indicators.iloc[-1]
        prev = df_with_indicators.iloc[-2]

        price = float(last['close'])
        ema9 = float(last['ema9'])
        ema21 = float(last['ema21'])
        rsi = float(last['rsi'])
        vwap = float(last.get('vwap', price))
        volume = float(last['volume'])
        vol_avg = float(last.get('vol_avg20', volume))

        # ── Technical Score Breakdown (Max 100) ──
        tech_score = 0.0

        # 1. Trend Alignment (35 pts)
        if ema9 > ema21:
            tech_score += 25.0
            if (ema9 - ema21) > (float(prev['ema9']) - float(prev['ema21'])):
                tech_score += 10.0  # Expanding moving average gap
        elif ema9 < ema21:
            tech_score += 5.0

        # 2. Momentum / RSI (30 pts)
        if rsi >= self.config.rsi_buy_level and rsi <= 70.0:
            tech_score += 30.0  # Strong bullish momentum without being overbought
        elif rsi > 70.0:
            tech_score += 15.0  # Overbought zone
        elif rsi >= 40.0:
            tech_score += 10.0

        # 3. Value Confirmation / VWAP (20 pts)
        if price > vwap:
            tech_score += 20.0
        elif price == vwap:
            tech_score += 10.0

        # 4. Volume Surge Confirmation (15 pts)
        if volume >= vol_avg * self.config.volume_multiplier:
            tech_score += 15.0
        elif volume >= vol_avg * 0.7:
            tech_score += 8.0

        # ── Signal Determination ──
        is_bullish_cross = ema9 > ema21
        is_rsi_confirmed = rsi >= self.config.rsi_buy_level
        is_above_vwap = price >= vwap
        is_volume_confirmed = volume >= (vol_avg * 0.8)

        if is_bullish_cross and is_rsi_confirmed and is_above_vwap and is_volume_confirmed:
            signal = "BUY SETUP"
        elif ema9 < ema21 and rsi < self.config.rsi_exit_level:
            signal = "EXIT"
        elif is_bullish_cross or (rsi >= 48.0 and price >= vwap):
            signal = "WATCH"
        else:
            signal = "NO TRADE"

        return {
            "signal": signal,
            "tech_score": round(tech_score, 1),
            "price": price,
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "rsi": round(rsi, 2),
            "vwap": round(vwap, 2),
            "volume": int(volume),
            "avg_volume": int(vol_avg),
        }
