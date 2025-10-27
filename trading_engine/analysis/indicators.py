"""
Technical indicators for trading analysis
"""

from typing import List, Optional
import pandas as pd
import numpy as np
from utils.logger import get_logger


logger = get_logger("indicators")


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """
    Calculate Simple Moving Average

    Args:
        prices: Price list
        period: SMA period

    Returns:
        List of SMA values
    """
    if len(prices) < period:
        return []

    df = pd.DataFrame({"price": prices})
    sma = df["price"].rolling(window=period).mean()
    return sma.fillna(0).tolist()


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average

    Args:
        prices: Price list
        period: EMA period

    Returns:
        List of EMA values
    """
    if len(prices) < period:
        return []

    df = pd.DataFrame({"price": prices})
    ema = df["price"].ewm(span=period, adjust=False).mean()
    return ema.fillna(0).tolist()


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index

    Args:
        prices: Price list
        period: RSI period

    Returns:
        List of RSI values
    """
    if len(prices) < period + 1:
        return []

    df = pd.DataFrame({"price": prices})
    delta = df["price"].diff()

    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50).tolist()


def calculate_bollinger_bands(
    prices: List[float],
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[List[float], List[float], List[float]]:
    """
    Calculate Bollinger Bands

    Args:
        prices: Price list
        period: Moving average period
        std_dev: Standard deviation multiplier

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    if len(prices) < period:
        return [], [], []

    df = pd.DataFrame({"price": prices})
    middle_band = df["price"].rolling(window=period).mean()
    std = df["price"].rolling(window=period).std()

    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return (
        upper_band.fillna(0).tolist(),
        middle_band.fillna(0).tolist(),
        lower_band.fillna(0).tolist()
    )


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> tuple[List[float], List[float], List[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence)

    Args:
        prices: Price list
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    if len(prices) < slow_period:
        return [], [], []

    df = pd.DataFrame({"price": prices})

    fast_ema = df["price"].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df["price"].ewm(span=slow_period, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return (
        macd_line.fillna(0).tolist(),
        signal_line.fillna(0).tolist(),
        histogram.fillna(0).tolist()
    )


def calculate_atr(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    period: int = 14
) -> List[float]:
    """
    Calculate Average True Range

    Args:
        highs: High prices
        lows: Low prices
        closes: Close prices
        period: ATR period

    Returns:
        List of ATR values
    """
    if len(highs) < period or len(lows) < period or len(closes) < period:
        return []

    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})

    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()

    return atr.fillna(0).tolist()


def detect_breakout(
    prices: List[float],
    high_threshold: float,
    low_threshold: float
) -> Optional[str]:
    """
    Detect price breakout

    Args:
        prices: Recent price list
        high_threshold: Upper breakout level
        low_threshold: Lower breakout level

    Returns:
        "BULLISH", "BEARISH", or None
    """
    if not prices:
        return None

    latest_price = prices[-1]

    if latest_price > high_threshold:
        return "BULLISH"
    elif latest_price < low_threshold:
        return "BEARISH"

    return None


def is_oversold(rsi_values: List[float], threshold: float = 30) -> bool:
    """
    Check if RSI indicates oversold condition

    Args:
        rsi_values: RSI values
        threshold: Oversold threshold

    Returns:
        True if oversold
    """
    if not rsi_values:
        return False

    return rsi_values[-1] < threshold


def is_overbought(rsi_values: List[float], threshold: float = 70) -> bool:
    """
    Check if RSI indicates overbought condition

    Args:
        rsi_values: RSI values
        threshold: Overbought threshold

    Returns:
        True if overbought
    """
    if not rsi_values:
        return False

    return rsi_values[-1] > threshold
