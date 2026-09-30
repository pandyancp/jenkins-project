"""
Technical Indicators Engine
===========================
Calculates EMA, RSI, VWAP, SMA, and ATR using pure NumPy & Pandas.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Union


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average (SMA)."""
    return series.rolling(window=period).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Where avg_loss is 0 and avg_gain > 0 -> RSI = 100
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    # Where avg_gain is 0 and avg_loss > 0 -> RSI = 0
    rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0.0)
    
    return rsi.fillna(50.0)


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).
    Requires 'high', 'low', 'close', 'volume' columns.
    """
    typical_price = (df['high'] + df['low'] + df['close']) / 3.0
    cum_tp_vol = (typical_price * df['volume']).cumsum()
    cum_vol = df['volume'].cumsum()
    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap.fillna(df['close'])


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) for volatility measurement."""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def attach_all_indicators(df: pd.DataFrame, ema_fast: int = 9, ema_slow: int = 21, rsi_period: int = 14) -> pd.DataFrame:
    """
    Computes and attaches all core technical indicators to an OHLCV dataframe.
    """
    df = df.copy()
    if len(df) == 0:
        return df

    # Lowercase standard columns
    col_map = {c: c.lower() for c in df.columns}
    df.rename(columns=col_map, inplace=True)

    df['ema9'] = calculate_ema(df['close'], ema_fast)
    df['ema21'] = calculate_ema(df['close'], ema_slow)
    df['rsi'] = calculate_rsi(df['close'], rsi_period)
    df['vwap'] = calculate_vwap(df)
    df['vol_avg20'] = calculate_sma(df['volume'], 20).fillna(df['volume'])
    df['atr14'] = calculate_atr(df, 14)

    return df
