"""
Chart pattern analyzer
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from data.market_data import Candle
from analysis.indicators import calculate_sma, calculate_rsi
from utils.logger import get_logger


logger = get_logger("chart_analyzer")


@dataclass
class ChartPattern:
    """Chart pattern detection result"""
    pattern_type: str
    confidence: float
    description: str
    direction: str  # BULLISH or BEARISH


class ChartAnalyzer:
    """
    Analyzes chart patterns and price action
    """

    def __init__(self):
        self.logger = logger

    def detect_higher_highs_lows(self, candles: List[Candle]) -> Optional[str]:
        """
        Detect higher highs and higher lows (uptrend)
        or lower highs and lower lows (downtrend)

        Args:
            candles: List of recent candles

        Returns:
            "UPTREND", "DOWNTREND", or None
        """
        if len(candles) < 3:
            return None

        highs = [c.high for c in candles[-3:]]
        lows = [c.low for c in candles[-3:]]

        # Check for uptrend
        higher_highs = highs[0] < highs[1] < highs[2]
        higher_lows = lows[0] < lows[1] < lows[2]

        if higher_highs and higher_lows:
            return "UPTREND"

        # Check for downtrend
        lower_highs = highs[0] > highs[1] > highs[2]
        lower_lows = lows[0] > lows[1] > lows[2]

        if lower_highs and lower_lows:
            return "DOWNTREND"

        return None

    def detect_ma_crossover(
        self,
        prices: List[float],
        fast_period: int = 10,
        slow_period: int = 20
    ) -> Optional[str]:
        """
        Detect moving average crossover

        Args:
            prices: Price list
            fast_period: Fast MA period
            slow_period: Slow MA period

        Returns:
            "BULLISH_CROSS", "BEARISH_CROSS", or None
        """
        if len(prices) < slow_period + 2:
            return None

        fast_ma = calculate_sma(prices, fast_period)
        slow_ma = calculate_sma(prices, slow_period)

        if not fast_ma or not slow_ma:
            return None

        # Check last two periods
        prev_fast = fast_ma[-2]
        curr_fast = fast_ma[-1]
        prev_slow = slow_ma[-2]
        curr_slow = slow_ma[-1]

        # Bullish crossover: fast MA crosses above slow MA
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return "BULLISH_CROSS"

        # Bearish crossover: fast MA crosses below slow MA
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return "BEARISH_CROSS"

        return None

    def analyze_price_action(self, candles: List[Candle]) -> Dict[str, Any]:
        """
        Analyze overall price action

        Args:
            candles: List of candles

        Returns:
            Dictionary with analysis results
        """
        if not candles:
            return {}

        prices = [c.close for c in candles]

        # Detect trend
        trend = self.detect_higher_highs_lows(candles)

        # Calculate RSI
        rsi_values = calculate_rsi(prices)
        current_rsi = rsi_values[-1] if rsi_values else 50

        # Detect MA crossover
        ma_cross = self.detect_ma_crossover(prices)

        # Calculate price momentum
        if len(prices) >= 2:
            price_change = prices[-1] - prices[-2]
            price_change_pct = (price_change / prices[-2]) * 100 if prices[-2] != 0 else 0
        else:
            price_change = 0
            price_change_pct = 0

        return {
            "trend": trend,
            "current_rsi": current_rsi,
            "ma_crossover": ma_cross,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "current_price": prices[-1] if prices else 0
        }
