"""
Trading Strategies
===================
Implements various technical analysis strategies that generate
BUY/SELL signals based on price data.

Available Strategies:
- SMA Crossover (Moving Average Crossover)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
"""

import numpy as np
import pandas as pd
import logging
from config import (
    SMA_FAST_PERIOD, SMA_SLOW_PERIOD,
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD_DEV
)

logger = logging.getLogger("GrowwBot")


# ═══════════════════════════════════════════════
# SIGNAL CONSTANTS
# ═══════════════════════════════════════════════
SIGNAL_BUY = "BUY"
SIGNAL_SELL = "SELL"
SIGNAL_HOLD = "HOLD"


def calculate_sma(prices, period):
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])


def calculate_ema(prices, period):
    """Calculate Exponential Moving Average."""
    if len(prices) < period:
        return None
    df = pd.Series(prices)
    return df.ewm(span=period, adjust=False).mean().iloc[-1]


def calculate_rsi(prices, period=14):
    """
    Calculate Relative Strength Index.
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    if len(prices) < period + 1:
        return None

    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Returns:
        tuple: (macd_line, signal_line, histogram)
    """
    if len(prices) < slow + signal:
        return None, None, None

    df = pd.Series(prices)
    ema_fast = df.ewm(span=fast, adjust=False).mean()
    ema_slow = df.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return (
        round(macd_line.iloc[-1], 4),
        round(signal_line.iloc[-1], 4),
        round(histogram.iloc[-1], 4)
    )


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """
    Calculate Bollinger Bands.
    
    Returns:
        tuple: (upper_band, middle_band, lower_band)
    """
    if len(prices) < period:
        return None, None, None

    df = pd.Series(prices[-period:])
    middle = df.mean()
    std = df.std()

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return round(upper, 2), round(middle, 2), round(lower, 2)


# ═══════════════════════════════════════════════
# STRATEGY IMPLEMENTATIONS
# ═══════════════════════════════════════════════

class BaseStrategy:
    """Base class for all trading strategies."""

    def __init__(self, name):
        self.name = name
        self.prices = []

    def add_price(self, price):
        """Add a new price to the price history."""
        self.prices.append(price)

    def get_signal(self):
        """Override in subclass. Returns SIGNAL_BUY, SIGNAL_SELL, or SIGNAL_HOLD."""
        raise NotImplementedError

    def get_info(self):
        """Override in subclass. Returns dict with indicator values."""
        return {}


class SMACrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    
    BUY:  Fast SMA crosses ABOVE slow SMA (Golden Cross)
    SELL: Fast SMA crosses BELOW slow SMA (Death Cross)
    """

    def __init__(self):
        super().__init__("SMA Crossover")
        self.fast_period = SMA_FAST_PERIOD
        self.slow_period = SMA_SLOW_PERIOD
        self.prev_fast = None
        self.prev_slow = None

    def get_signal(self):
        if len(self.prices) < self.slow_period + 1:
            return SIGNAL_HOLD

        fast_sma = calculate_sma(self.prices, self.fast_period)
        slow_sma = calculate_sma(self.prices, self.slow_period)

        # Calculate previous SMAs for crossover detection
        prev_fast = calculate_sma(self.prices[:-1], self.fast_period)
        prev_slow = calculate_sma(self.prices[:-1], self.slow_period)

        if prev_fast is None or prev_slow is None:
            return SIGNAL_HOLD

        signal = SIGNAL_HOLD

        # Golden Cross: Fast SMA crosses above Slow SMA
        if prev_fast <= prev_slow and fast_sma > slow_sma:
            signal = SIGNAL_BUY
            logger.info(
                f"📈 SMA GOLDEN CROSS | Fast({self.fast_period})={fast_sma:.2f} "
                f"> Slow({self.slow_period})={slow_sma:.2f}"
            )

        # Death Cross: Fast SMA crosses below Slow SMA
        elif prev_fast >= prev_slow and fast_sma < slow_sma:
            signal = SIGNAL_SELL
            logger.info(
                f"📉 SMA DEATH CROSS | Fast({self.fast_period})={fast_sma:.2f} "
                f"< Slow({self.slow_period})={slow_sma:.2f}"
            )

        self.prev_fast = fast_sma
        self.prev_slow = slow_sma
        return signal

    def get_info(self):
        fast = calculate_sma(self.prices, self.fast_period)
        slow = calculate_sma(self.prices, self.slow_period)
        return {
            "strategy": self.name,
            f"SMA_{self.fast_period}": round(fast, 2) if fast else "N/A",
            f"SMA_{self.slow_period}": round(slow, 2) if slow else "N/A",
            "trend": "BULLISH" if fast and slow and fast > slow else "BEARISH",
        }


class RSIStrategy(BaseStrategy):
    """
    Relative Strength Index Strategy.
    
    BUY:  RSI falls below oversold level (30) then rises
    SELL: RSI rises above overbought level (70) then falls
    """

    def __init__(self):
        super().__init__("RSI")
        self.period = RSI_PERIOD
        self.overbought = RSI_OVERBOUGHT
        self.oversold = RSI_OVERSOLD
        self.prev_rsi = None

    def get_signal(self):
        if len(self.prices) < self.period + 2:
            return SIGNAL_HOLD

        current_rsi = calculate_rsi(self.prices, self.period)
        prev_rsi = calculate_rsi(self.prices[:-1], self.period)

        if current_rsi is None or prev_rsi is None:
            return SIGNAL_HOLD

        signal = SIGNAL_HOLD

        # Buy when RSI crosses above oversold
        if prev_rsi <= self.oversold and current_rsi > self.oversold:
            signal = SIGNAL_BUY
            logger.info(f"📈 RSI BUY SIGNAL | RSI: {prev_rsi:.1f} → {current_rsi:.1f} (crossed above {self.oversold})")

        # Sell when RSI crosses below overbought
        elif prev_rsi >= self.overbought and current_rsi < self.overbought:
            signal = SIGNAL_SELL
            logger.info(f"📉 RSI SELL SIGNAL | RSI: {prev_rsi:.1f} → {current_rsi:.1f} (crossed below {self.overbought})")

        self.prev_rsi = current_rsi
        return signal

    def get_info(self):
        rsi = calculate_rsi(self.prices, self.period)
        zone = "NEUTRAL"
        if rsi:
            if rsi >= self.overbought:
                zone = "OVERBOUGHT"
            elif rsi <= self.oversold:
                zone = "OVERSOLD"
        return {
            "strategy": self.name,
            "RSI": rsi if rsi else "N/A",
            "zone": zone,
        }


class MACDStrategy(BaseStrategy):
    """
    MACD Strategy.
    
    BUY:  MACD line crosses above Signal line
    SELL: MACD line crosses below Signal line
    """

    def __init__(self):
        super().__init__("MACD")
        self.fast = MACD_FAST
        self.slow = MACD_SLOW
        self.signal_period = MACD_SIGNAL

    def get_signal(self):
        if len(self.prices) < self.slow + self.signal_period + 1:
            return SIGNAL_HOLD

        macd, signal_line, histogram = calculate_macd(
            self.prices, self.fast, self.slow, self.signal_period
        )
        prev_macd, prev_signal, _ = calculate_macd(
            self.prices[:-1], self.fast, self.slow, self.signal_period
        )

        if any(v is None for v in [macd, signal_line, prev_macd, prev_signal]):
            return SIGNAL_HOLD

        result = SIGNAL_HOLD

        # Bullish crossover
        if prev_macd <= prev_signal and macd > signal_line:
            result = SIGNAL_BUY
            logger.info(f"📈 MACD BUY | MACD={macd:.4f} > Signal={signal_line:.4f}")

        # Bearish crossover
        elif prev_macd >= prev_signal and macd < signal_line:
            result = SIGNAL_SELL
            logger.info(f"📉 MACD SELL | MACD={macd:.4f} < Signal={signal_line:.4f}")

        return result

    def get_info(self):
        macd, signal_line, histogram = calculate_macd(
            self.prices, self.fast, self.slow, self.signal_period
        )
        return {
            "strategy": self.name,
            "MACD": macd if macd else "N/A",
            "Signal": signal_line if signal_line else "N/A",
            "Histogram": histogram if histogram else "N/A",
        }


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    
    BUY:  Price touches or goes below the lower band
    SELL: Price touches or goes above the upper band
    """

    def __init__(self):
        super().__init__("Bollinger Bands")
        self.period = BB_PERIOD
        self.std_dev = BB_STD_DEV

    def get_signal(self):
        if len(self.prices) < self.period + 1:
            return SIGNAL_HOLD

        upper, middle, lower = calculate_bollinger_bands(
            self.prices, self.period, self.std_dev
        )
        current_price = self.prices[-1]

        if any(v is None for v in [upper, middle, lower]):
            return SIGNAL_HOLD

        signal = SIGNAL_HOLD

        # Price at or below lower band → Buy
        if current_price <= lower:
            signal = SIGNAL_BUY
            logger.info(
                f"📈 BB BUY | Price={current_price:.2f} ≤ Lower={lower:.2f}"
            )

        # Price at or above upper band → Sell
        elif current_price >= upper:
            signal = SIGNAL_SELL
            logger.info(
                f"📉 BB SELL | Price={current_price:.2f} ≥ Upper={upper:.2f}"
            )

        return signal

    def get_info(self):
        upper, middle, lower = calculate_bollinger_bands(
            self.prices, self.period, self.std_dev
        )
        return {
            "strategy": self.name,
            "Upper": upper if upper else "N/A",
            "Middle": middle if middle else "N/A",
            "Lower": lower if lower else "N/A",
            "Price": self.prices[-1] if self.prices else "N/A",
        }


# ═══════════════════════════════════════════════
# STRATEGY FACTORY
# ═══════════════════════════════════════════════

def get_strategy(name):
    """
    Factory function to get strategy instance by name.
    
    Args:
        name: Strategy name (SMA_CROSSOVER, RSI, MACD, BOLLINGER)
        
    Returns:
        Strategy instance
    """
    strategies = {
        "SMA_CROSSOVER": SMACrossoverStrategy,
        "RSI": RSIStrategy,
        "MACD": MACDStrategy,
        "BOLLINGER": BollingerBandsStrategy,
    }

    if name not in strategies:
        logger.warning(f"Unknown strategy '{name}', defaulting to SMA Crossover")
        return SMACrossoverStrategy()

    return strategies[name]()
