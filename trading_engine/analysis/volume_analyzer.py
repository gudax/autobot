"""
Volume Analyzer - Detects volume spikes and analyzes buy/sell pressure
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np

from config.strategy_config import VolumeAnalysisConfig
from data.market_data import Candle
from utils.logger import get_logger
from utils.helpers import calculate_moving_average


logger = get_logger("volume_analyzer")


class SignalDirection(str, Enum):
    """Signal direction"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


@dataclass
class VolumeSignal:
    """
    Volume-based trading signal
    """
    symbol: str
    direction: SignalDirection
    strength: float  # 0.0 to 1.0
    volume_ratio: float  # Current volume / Average volume
    buy_sell_ratio: float  # Buy volume / (Buy + Sell volume)
    timestamp: int
    price: float
    volume: float
    avg_volume: float
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": self.strength,
            "volume_ratio": self.volume_ratio,
            "buy_sell_ratio": self.buy_sell_ratio,
            "timestamp": self.timestamp,
            "price": self.price,
            "volume": self.volume,
            "avg_volume": self.avg_volume,
            "reason": self.reason
        }


class VolumeAnalyzer:
    """
    Analyzes trading volume to detect spikes and directional pressure
    """

    def __init__(self, config: Optional[VolumeAnalysisConfig] = None):
        """
        Initialize Volume Analyzer

        Args:
            config: Volume analysis configuration
        """
        self.config = config or VolumeAnalysisConfig()
        self.logger = logger

        # Storage for historical data
        self.volume_history: Dict[str, List[float]] = {}
        self.buy_volume_history: Dict[str, List[float]] = {}
        self.sell_volume_history: Dict[str, List[float]] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.timestamp_history: Dict[str, List[int]] = {}

        # Cache for moving averages
        self.ma_cache: Dict[str, Dict[int, float]] = {}

    def add_candle(self, candle: Candle) -> None:
        """
        Add candle data to history

        Args:
            candle: Candle data
        """
        symbol = candle.symbol

        # Initialize lists if not exist
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
            self.buy_volume_history[symbol] = []
            self.sell_volume_history[symbol] = []
            self.price_history[symbol] = []
            self.timestamp_history[symbol] = []

        # Add data
        self.volume_history[symbol].append(candle.volume)
        self.buy_volume_history[symbol].append(candle.buy_volume)
        self.sell_volume_history[symbol].append(candle.sell_volume)
        self.price_history[symbol].append(candle.close)
        self.timestamp_history[symbol].append(candle.timestamp)

        # Keep only recent data (e.g., last 200 candles)
        max_history = max(self.config.ma_periods) * 2 if self.config.ma_periods else 200

        if len(self.volume_history[symbol]) > max_history:
            self.volume_history[symbol] = self.volume_history[symbol][-max_history:]
            self.buy_volume_history[symbol] = self.buy_volume_history[symbol][-max_history:]
            self.sell_volume_history[symbol] = self.sell_volume_history[symbol][-max_history:]
            self.price_history[symbol] = self.price_history[symbol][-max_history:]
            self.timestamp_history[symbol] = self.timestamp_history[symbol][-max_history:]

        # Clear cache when new data added
        if symbol in self.ma_cache:
            self.ma_cache.pop(symbol)

    def add_candles(self, candles: List[Candle]) -> None:
        """
        Add multiple candles to history

        Args:
            candles: List of candle data
        """
        for candle in candles:
            self.add_candle(candle)

    def calculate_volume_ma(self, symbol: str, period: int) -> Optional[float]:
        """
        Calculate volume moving average

        Args:
            symbol: Trading symbol
            period: Moving average period

        Returns:
            Moving average value or None
        """
        if symbol not in self.volume_history:
            return None

        volumes = self.volume_history[symbol]

        if len(volumes) < period:
            return None

        # Check cache
        if symbol in self.ma_cache and period in self.ma_cache[symbol]:
            return self.ma_cache[symbol][period]

        # Calculate MA
        ma = np.mean(volumes[-period:])

        # Cache result
        if symbol not in self.ma_cache:
            self.ma_cache[symbol] = {}
        self.ma_cache[symbol][period] = ma

        return ma

    def detect_volume_spike(
        self,
        symbol: str,
        current_volume: float,
        ma_period: int = 20
    ) -> Dict[str, Any]:
        """
        Detect if current volume is a spike

        Args:
            symbol: Trading symbol
            current_volume: Current volume
            ma_period: Moving average period for comparison

        Returns:
            Dictionary with spike detection results
        """
        avg_volume = self.calculate_volume_ma(symbol, ma_period)

        if avg_volume is None or avg_volume == 0:
            return {
                "is_spike": False,
                "volume_ratio": 1.0,
                "spike_level": "normal",
                "avg_volume": 0
            }

        volume_ratio = current_volume / avg_volume

        # Determine spike level
        spike_level = "normal"
        is_spike = False

        if volume_ratio >= self.config.spike_threshold_high:
            spike_level = "high"
            is_spike = True
        elif volume_ratio >= self.config.spike_threshold_medium:
            spike_level = "medium"
            is_spike = True
        elif volume_ratio >= self.config.spike_threshold_low:
            spike_level = "low"
            is_spike = True

        return {
            "is_spike": is_spike,
            "volume_ratio": volume_ratio,
            "spike_level": spike_level,
            "avg_volume": avg_volume,
            "current_volume": current_volume
        }

    def calculate_buy_sell_ratio(
        self,
        symbol: str,
        current_buy_volume: float,
        current_sell_volume: float
    ) -> Dict[str, Any]:
        """
        Calculate buy/sell volume ratio

        Args:
            symbol: Trading symbol
            current_buy_volume: Current buy volume
            current_sell_volume: Current sell volume

        Returns:
            Dictionary with ratio analysis
        """
        total_volume = current_buy_volume + current_sell_volume

        if total_volume == 0:
            return {
                "buy_ratio": 0.5,
                "sell_ratio": 0.5,
                "direction": SignalDirection.NEUTRAL,
                "pressure": "neutral"
            }

        buy_ratio = current_buy_volume / total_volume
        sell_ratio = current_sell_volume / total_volume

        # Determine direction
        if buy_ratio >= self.config.buy_sell_ratio_threshold:
            direction = SignalDirection.LONG
            pressure = "strong_buy" if buy_ratio >= 0.7 else "buy"
        elif sell_ratio >= self.config.buy_sell_ratio_threshold:
            direction = SignalDirection.SHORT
            pressure = "strong_sell" if sell_ratio >= 0.7 else "sell"
        else:
            direction = SignalDirection.NEUTRAL
            pressure = "neutral"

        return {
            "buy_ratio": buy_ratio,
            "sell_ratio": sell_ratio,
            "direction": direction,
            "pressure": pressure,
            "buy_volume": current_buy_volume,
            "sell_volume": current_sell_volume
        }

    def check_consecutive_direction(
        self,
        symbol: str,
        min_consecutive: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if recent candles are moving in the same direction

        Args:
            symbol: Trading symbol
            min_consecutive: Minimum consecutive candles (uses config if None)

        Returns:
            Dictionary with consecutive analysis
        """
        if min_consecutive is None:
            min_consecutive = self.config.min_consecutive_candles

        if symbol not in self.price_history:
            return {
                "has_consecutive": False,
                "direction": SignalDirection.NEUTRAL,
                "count": 0
            }

        prices = self.price_history[symbol]

        if len(prices) < min_consecutive + 1:
            return {
                "has_consecutive": False,
                "direction": SignalDirection.NEUTRAL,
                "count": 0
            }

        # Check last N candles
        recent_prices = prices[-(min_consecutive + 1):]

        # Determine direction
        all_up = all(
            recent_prices[i] < recent_prices[i + 1]
            for i in range(len(recent_prices) - 1)
        )

        all_down = all(
            recent_prices[i] > recent_prices[i + 1]
            for i in range(len(recent_prices) - 1)
        )

        if all_up:
            direction = SignalDirection.LONG
            has_consecutive = True
            count = min_consecutive
        elif all_down:
            direction = SignalDirection.SHORT
            has_consecutive = True
            count = min_consecutive
        else:
            direction = SignalDirection.NEUTRAL
            has_consecutive = False
            count = 0

        return {
            "has_consecutive": has_consecutive,
            "direction": direction,
            "count": count
        }

    def calculate_signal_strength(
        self,
        volume_spike: Dict[str, Any],
        buy_sell_analysis: Dict[str, Any],
        consecutive_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate overall signal strength (0.0 to 1.0)

        Args:
            volume_spike: Volume spike detection results
            buy_sell_analysis: Buy/sell ratio analysis
            consecutive_analysis: Consecutive direction analysis

        Returns:
            Signal strength score
        """
        strength = 0.0

        # Volume spike contribution (40%)
        if volume_spike["is_spike"]:
            volume_ratio = volume_spike["volume_ratio"]
            spike_level = volume_spike["spike_level"]

            if spike_level == "high":
                strength += 0.4
            elif spike_level == "medium":
                strength += 0.3
            elif spike_level == "low":
                strength += 0.2

        # Buy/sell ratio contribution (40%)
        pressure = buy_sell_analysis["pressure"]
        if pressure in ["strong_buy", "strong_sell"]:
            strength += 0.4
        elif pressure in ["buy", "sell"]:
            strength += 0.25

        # Consecutive direction contribution (20%)
        if consecutive_analysis["has_consecutive"]:
            strength += 0.2

        return min(strength, 1.0)

    def analyze(
        self,
        symbol: str,
        current_candle: Candle,
        ma_period: int = 20
    ) -> Optional[VolumeSignal]:
        """
        Analyze current volume and generate signal

        Args:
            symbol: Trading symbol
            current_candle: Current candle data
            ma_period: Moving average period

        Returns:
            VolumeSignal or None if no signal
        """
        # Add candle to history
        self.add_candle(current_candle)

        # Detect volume spike
        volume_spike = self.detect_volume_spike(
            symbol,
            current_candle.volume,
            ma_period
        )

        # Calculate buy/sell ratio
        buy_sell_analysis = self.calculate_buy_sell_ratio(
            symbol,
            current_candle.buy_volume,
            current_candle.sell_volume
        )

        # Check consecutive direction
        consecutive_analysis = self.check_consecutive_direction(symbol)

        # Calculate signal strength
        strength = self.calculate_signal_strength(
            volume_spike,
            buy_sell_analysis,
            consecutive_analysis
        )

        # Determine final direction
        direction = SignalDirection.NEUTRAL

        if volume_spike["is_spike"]:
            # Use buy/sell ratio direction if volume spike detected
            direction = buy_sell_analysis["direction"]

            # Confirm with consecutive direction if available
            if consecutive_analysis["has_consecutive"]:
                if consecutive_analysis["direction"] != buy_sell_analysis["direction"]:
                    # Conflict - reduce strength
                    strength *= 0.7
                    direction = SignalDirection.NEUTRAL

        # Build reason string
        reasons = []
        if volume_spike["is_spike"]:
            reasons.append(
                f"Volume spike ({volume_spike['spike_level']}: "
                f"{volume_spike['volume_ratio']:.2f}x avg)"
            )
        if buy_sell_analysis["pressure"] != "neutral":
            reasons.append(f"{buy_sell_analysis['pressure']} pressure")
        if consecutive_analysis["has_consecutive"]:
            reasons.append(f"{consecutive_analysis['count']} consecutive candles")

        reason = " + ".join(reasons) if reasons else "No significant signal"

        # Create signal
        signal = VolumeSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            volume_ratio=volume_spike["volume_ratio"],
            buy_sell_ratio=buy_sell_analysis["buy_ratio"],
            timestamp=current_candle.timestamp,
            price=current_candle.close,
            volume=current_candle.volume,
            avg_volume=volume_spike["avg_volume"],
            reason=reason
        )

        self.logger.info(
            "Volume analysis complete",
            symbol=symbol,
            direction=direction.value,
            strength=strength,
            volume_ratio=volume_spike["volume_ratio"]
        )

        return signal

    def get_statistics(self, symbol: str) -> Dict[str, Any]:
        """
        Get volume statistics for symbol

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with statistics
        """
        if symbol not in self.volume_history:
            return {}

        volumes = self.volume_history[symbol]
        buy_volumes = self.buy_volume_history[symbol]
        sell_volumes = self.sell_volume_history[symbol]

        if not volumes:
            return {}

        # Calculate statistics
        stats = {
            "symbol": symbol,
            "candle_count": len(volumes),
            "avg_volume": np.mean(volumes),
            "max_volume": np.max(volumes),
            "min_volume": np.min(volumes),
            "std_volume": np.std(volumes),
            "avg_buy_volume": np.mean(buy_volumes) if buy_volumes else 0,
            "avg_sell_volume": np.mean(sell_volumes) if sell_volumes else 0,
        }

        # Calculate moving averages
        for period in self.config.ma_periods:
            ma = self.calculate_volume_ma(symbol, period)
            if ma:
                stats[f"ma_{period}"] = ma

        return stats

    def clear_history(self, symbol: Optional[str] = None) -> None:
        """
        Clear volume history

        Args:
            symbol: Symbol to clear (None = clear all)
        """
        if symbol:
            self.volume_history.pop(symbol, None)
            self.buy_volume_history.pop(symbol, None)
            self.sell_volume_history.pop(symbol, None)
            self.price_history.pop(symbol, None)
            self.timestamp_history.pop(symbol, None)
            self.ma_cache.pop(symbol, None)
            self.logger.info("Volume history cleared", symbol=symbol)
        else:
            self.volume_history.clear()
            self.buy_volume_history.clear()
            self.sell_volume_history.clear()
            self.price_history.clear()
            self.timestamp_history.clear()
            self.ma_cache.clear()
            self.logger.info("All volume history cleared")
