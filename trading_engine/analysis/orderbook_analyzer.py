"""
Order Book Analyzer - Analyzes order book to detect buy/sell pressure
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum

from config.strategy_config import OrderBookConfig
from data.orderbook import OrderBook, OrderBookLevel
from utils.logger import get_logger


logger = get_logger("orderbook_analyzer")


class OrderBookPressure(str, Enum):
    """Order book pressure direction"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    NEUTRAL = "NEUTRAL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class OrderBookAnalysis:
    """
    Order book analysis results
    """
    symbol: str
    imbalance_ratio: float  # 0.5 = balanced, >0.5 = buy pressure, <0.5 = sell pressure
    spread_bps: float  # Spread in basis points
    large_bid_detected: bool
    large_ask_detected: bool
    resistance_levels: List[float]
    support_levels: List[float]
    liquidity_score: float  # 0.0 to 1.0
    pressure: OrderBookPressure
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "imbalance_ratio": self.imbalance_ratio,
            "spread_bps": self.spread_bps,
            "large_bid_detected": self.large_bid_detected,
            "large_ask_detected": self.large_ask_detected,
            "resistance_levels": self.resistance_levels,
            "support_levels": self.support_levels,
            "liquidity_score": self.liquidity_score,
            "pressure": self.pressure.value,
            "timestamp": self.timestamp
        }


class OrderBookAnalyzer:
    """
    Analyzes order book to measure market pressure and liquidity
    """

    def __init__(self, config: Optional[OrderBookConfig] = None):
        """
        Initialize OrderBook Analyzer

        Args:
            config: OrderBook analysis configuration
        """
        self.config = config or OrderBookConfig()
        self.logger = logger

    def calculate_imbalance(self, orderbook: OrderBook) -> Dict[str, Any]:
        """
        Calculate order book imbalance

        Args:
            orderbook: OrderBook instance

        Returns:
            Dictionary with imbalance analysis
        """
        # Get volume at specified depth
        volumes = orderbook.get_volume_at_levels(self.config.order_book_depth)

        bid_volume = volumes["bid_volume"]
        ask_volume = volumes["ask_volume"]
        total_volume = volumes["total_volume"]
        ratio = volumes["ratio"]

        # Determine pressure
        if ratio >= 0.65:
            pressure = OrderBookPressure.STRONG_BUY
        elif ratio >= self.config.imbalance_threshold:
            pressure = OrderBookPressure.BUY
        elif ratio <= 0.35:
            pressure = OrderBookPressure.STRONG_SELL
        elif ratio <= (1 - self.config.imbalance_threshold):
            pressure = OrderBookPressure.SELL
        else:
            pressure = OrderBookPressure.NEUTRAL

        return {
            "imbalance_ratio": ratio,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "total_volume": total_volume,
            "pressure": pressure
        }

    def analyze_spread(self, orderbook: OrderBook) -> Dict[str, Any]:
        """
        Analyze bid-ask spread

        Args:
            orderbook: OrderBook instance

        Returns:
            Dictionary with spread analysis
        """
        spread = orderbook.spread
        spread_bps = orderbook.spread_bps

        # Check if spread is acceptable
        is_acceptable = spread_bps <= self.config.max_spread_bps

        # Determine spread quality
        if spread_bps <= 5:
            quality = "excellent"
        elif spread_bps <= 10:
            quality = "good"
        elif spread_bps <= 20:
            quality = "acceptable"
        else:
            quality = "wide"

        return {
            "spread": spread,
            "spread_bps": spread_bps,
            "is_acceptable": is_acceptable,
            "quality": quality,
            "best_bid": orderbook.best_bid.price if orderbook.best_bid else 0,
            "best_ask": orderbook.best_ask.price if orderbook.best_ask else 0,
            "mid_price": orderbook.mid_price
        }

    def detect_large_orders(self, orderbook: OrderBook) -> Dict[str, Any]:
        """
        Detect large orders in order book

        Args:
            orderbook: OrderBook instance

        Returns:
            Dictionary with large order detection
        """
        large_orders = orderbook.detect_large_orders(
            num_levels=self.config.order_book_depth,
            threshold_ratio=self.config.large_order_threshold
        )

        has_large_bids = len(large_orders["large_bids"]) > 0
        has_large_asks = len(large_orders["large_asks"]) > 0

        # Analyze implications
        if has_large_bids and not has_large_asks:
            implication = "strong_support"
        elif has_large_asks and not has_large_bids:
            implication = "strong_resistance"
        elif has_large_bids and has_large_asks:
            implication = "range_bound"
        else:
            implication = "no_significant_orders"

        return {
            "large_bids": large_orders["large_bids"],
            "large_asks": large_orders["large_asks"],
            "bid_count": large_orders["bid_count"],
            "ask_count": large_orders["ask_count"],
            "has_large_bids": has_large_bids,
            "has_large_asks": has_large_asks,
            "implication": implication
        }

    def find_support_resistance(self, orderbook: OrderBook) -> Dict[str, Any]:
        """
        Find support and resistance levels based on order book

        Args:
            orderbook: OrderBook instance

        Returns:
            Dictionary with support/resistance levels
        """
        levels = orderbook.find_support_resistance(
            num_levels=self.config.order_book_depth,
            volume_threshold=self.config.large_order_threshold
        )

        support_levels = levels["support"]
        resistance_levels = levels["resistance"]

        # Find strongest levels (closest to current price)
        mid_price = orderbook.mid_price

        if support_levels:
            strongest_support = max(
                support_levels,
                key=lambda x: -abs(x - mid_price) if x < mid_price else -float('inf')
            )
        else:
            strongest_support = None

        if resistance_levels:
            strongest_resistance = min(
                resistance_levels,
                key=lambda x: abs(x - mid_price) if x > mid_price else float('inf')
            )
        else:
            strongest_resistance = None

        return {
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "strongest_support": strongest_support,
            "strongest_resistance": strongest_resistance,
            "support_count": len(support_levels),
            "resistance_count": len(resistance_levels)
        }

    def calculate_liquidity_score(self, orderbook: OrderBook) -> float:
        """
        Calculate liquidity score (0.0 to 1.0)

        Args:
            orderbook: OrderBook instance

        Returns:
            Liquidity score
        """
        score = 0.0

        # Factor 1: Total volume (30%)
        volumes = orderbook.get_volume_at_levels(self.config.order_book_depth)
        total_volume = volumes["total_volume"]

        # Normalize volume (assume good liquidity at 100+ volume)
        volume_score = min(total_volume / 100.0, 1.0) * 0.3
        score += volume_score

        # Factor 2: Spread quality (30%)
        spread_bps = orderbook.spread_bps

        if spread_bps <= 5:
            spread_score = 0.3
        elif spread_bps <= 10:
            spread_score = 0.25
        elif spread_bps <= 20:
            spread_score = 0.15
        else:
            spread_score = max(0, 0.3 - (spread_bps - 20) * 0.01)

        score += spread_score

        # Factor 3: Order book balance (20%)
        imbalance = orderbook.bid_ask_volume_ratio
        balance_score = (1 - abs(imbalance - 0.5) * 2) * 0.2
        score += balance_score

        # Factor 4: Number of price levels (20%)
        bid_levels = len(orderbook.bids)
        ask_levels = len(orderbook.asks)
        total_levels = bid_levels + ask_levels

        # Normalize (assume good depth at 20+ levels each side)
        levels_score = min(total_levels / 40.0, 1.0) * 0.2
        score += levels_score

        return min(score, 1.0)

    def analyze(self, orderbook: OrderBook) -> OrderBookAnalysis:
        """
        Perform complete order book analysis

        Args:
            orderbook: OrderBook instance

        Returns:
            OrderBookAnalysis results
        """
        # Calculate imbalance
        imbalance = self.calculate_imbalance(orderbook)

        # Analyze spread
        spread_analysis = self.analyze_spread(orderbook)

        # Detect large orders
        large_orders = self.detect_large_orders(orderbook)

        # Find support/resistance
        support_resistance = self.find_support_resistance(orderbook)

        # Calculate liquidity
        liquidity_score = self.calculate_liquidity_score(orderbook)

        # Create analysis result
        analysis = OrderBookAnalysis(
            symbol=orderbook.symbol,
            imbalance_ratio=imbalance["imbalance_ratio"],
            spread_bps=spread_analysis["spread_bps"],
            large_bid_detected=large_orders["has_large_bids"],
            large_ask_detected=large_orders["has_large_asks"],
            resistance_levels=support_resistance["resistance_levels"],
            support_levels=support_resistance["support_levels"],
            liquidity_score=liquidity_score,
            pressure=imbalance["pressure"],
            timestamp=orderbook.timestamp
        )

        self.logger.info(
            "Order book analysis complete",
            symbol=orderbook.symbol,
            pressure=analysis.pressure.value,
            imbalance_ratio=analysis.imbalance_ratio,
            liquidity_score=analysis.liquidity_score
        )

        return analysis

    def is_favorable_for_entry(
        self,
        analysis: OrderBookAnalysis,
        direction: str
    ) -> Dict[str, Any]:
        """
        Check if order book conditions are favorable for entry

        Args:
            analysis: OrderBookAnalysis results
            direction: Trade direction ("LONG" or "SHORT")

        Returns:
            Dictionary with favorability assessment
        """
        favorable = False
        reasons = []
        score = 0.0

        direction = direction.upper()

        # Check spread
        if analysis.spread_bps <= self.config.max_spread_bps:
            score += 0.2
            reasons.append("Acceptable spread")
        else:
            reasons.append("Spread too wide")

        # Check liquidity
        if analysis.liquidity_score >= self.config.min_liquidity_score:
            score += 0.2
            reasons.append("Good liquidity")
        else:
            reasons.append("Low liquidity")

        # Check pressure alignment
        if direction == "LONG":
            if analysis.pressure in [OrderBookPressure.BUY, OrderBookPressure.STRONG_BUY]:
                score += 0.3
                reasons.append("Buy pressure aligned")
            elif analysis.pressure == OrderBookPressure.NEUTRAL:
                score += 0.1
                reasons.append("Neutral pressure")
            else:
                reasons.append("Sell pressure against entry")

            # Check for support
            if analysis.support_levels:
                score += 0.15
                reasons.append("Support levels present")

            # Check large bids
            if analysis.large_bid_detected:
                score += 0.15
                reasons.append("Large bids detected")

        else:  # SHORT
            if analysis.pressure in [OrderBookPressure.SELL, OrderBookPressure.STRONG_SELL]:
                score += 0.3
                reasons.append("Sell pressure aligned")
            elif analysis.pressure == OrderBookPressure.NEUTRAL:
                score += 0.1
                reasons.append("Neutral pressure")
            else:
                reasons.append("Buy pressure against entry")

            # Check for resistance
            if analysis.resistance_levels:
                score += 0.15
                reasons.append("Resistance levels present")

            # Check large asks
            if analysis.large_ask_detected:
                score += 0.15
                reasons.append("Large asks detected")

        # Overall assessment
        if score >= 0.7:
            favorable = True
            assessment = "highly_favorable"
        elif score >= 0.5:
            favorable = True
            assessment = "favorable"
        elif score >= 0.3:
            assessment = "neutral"
        else:
            assessment = "unfavorable"

        return {
            "favorable": favorable,
            "score": score,
            "assessment": assessment,
            "reasons": reasons,
            "direction": direction
        }

    def compare_orderbooks(
        self,
        current: OrderBook,
        previous: OrderBook
    ) -> Dict[str, Any]:
        """
        Compare two order books to detect changes

        Args:
            current: Current order book
            previous: Previous order book

        Returns:
            Dictionary with comparison results
        """
        # Compare volumes
        current_bid_volume = current.total_bid_volume
        previous_bid_volume = previous.total_bid_volume
        current_ask_volume = current.total_ask_volume
        previous_ask_volume = previous.total_ask_volume

        bid_volume_change = current_bid_volume - previous_bid_volume
        ask_volume_change = current_ask_volume - previous_ask_volume

        bid_volume_change_pct = (
            (bid_volume_change / previous_bid_volume * 100)
            if previous_bid_volume > 0 else 0
        )

        ask_volume_change_pct = (
            (ask_volume_change / previous_ask_volume * 100)
            if previous_ask_volume > 0 else 0
        )

        # Compare spreads
        spread_change = current.spread - previous.spread
        spread_change_pct = (
            (spread_change / previous.spread * 100)
            if previous.spread > 0 else 0
        )

        # Compare imbalance
        current_ratio = current.bid_ask_volume_ratio
        previous_ratio = previous.bid_ask_volume_ratio
        imbalance_change = current_ratio - previous_ratio

        # Detect significant changes
        significant_changes = []

        if abs(bid_volume_change_pct) > 20:
            significant_changes.append(
                f"Bid volume {'+' if bid_volume_change > 0 else ''}{bid_volume_change_pct:.1f}%"
            )

        if abs(ask_volume_change_pct) > 20:
            significant_changes.append(
                f"Ask volume {'+' if ask_volume_change > 0 else ''}{ask_volume_change_pct:.1f}%"
            )

        if abs(imbalance_change) > 0.1:
            significant_changes.append(
                f"Imbalance shifted {'+' if imbalance_change > 0 else ''}{imbalance_change:.2f}"
            )

        return {
            "bid_volume_change": bid_volume_change,
            "bid_volume_change_pct": bid_volume_change_pct,
            "ask_volume_change": ask_volume_change,
            "ask_volume_change_pct": ask_volume_change_pct,
            "spread_change": spread_change,
            "spread_change_pct": spread_change_pct,
            "imbalance_change": imbalance_change,
            "significant_changes": significant_changes,
            "has_significant_changes": len(significant_changes) > 0
        }
