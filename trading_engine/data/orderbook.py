"""
Order Book data structure and collection
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from utils.logger import get_logger


logger = get_logger("orderbook")


@dataclass
class OrderBookLevel:
    """Single order book level"""
    price: float
    volume: float
    orders_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": self.price,
            "volume": self.volume,
            "orders_count": self.orders_count
        }


@dataclass
class OrderBook:
    """
    Order Book data structure
    Contains bid and ask levels
    """
    symbol: str
    bids: List[OrderBookLevel] = field(default_factory=list)
    asks: List[OrderBookLevel] = field(default_factory=list)
    timestamp: int = field(default_factory=lambda: int(datetime.utcnow().timestamp()))

    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Get best bid (highest price)"""
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Get best ask (lowest price)"""
        return self.asks[0] if self.asks else None

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return 0.0

    @property
    def spread_bps(self) -> float:
        """Calculate spread in basis points"""
        if self.best_bid and self.best_ask and self.best_bid.price > 0:
            return (self.spread / self.best_bid.price) * 10000
        return 0.0

    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return 0.0

    @property
    def total_bid_volume(self) -> float:
        """Calculate total bid volume"""
        return sum(level.volume for level in self.bids)

    @property
    def total_ask_volume(self) -> float:
        """Calculate total ask volume"""
        return sum(level.volume for level in self.asks)

    @property
    def bid_ask_volume_ratio(self) -> float:
        """
        Calculate bid/ask volume ratio
        > 0.5 means more bid volume (buy pressure)
        < 0.5 means more ask volume (sell pressure)
        """
        total = self.total_bid_volume + self.total_ask_volume
        if total > 0:
            return self.total_bid_volume / total
        return 0.5

    def get_volume_at_levels(self, num_levels: int = 10) -> Dict[str, float]:
        """
        Get total volume at specified number of levels

        Args:
            num_levels: Number of levels to include

        Returns:
            Dictionary with bid_volume and ask_volume
        """
        bid_volume = sum(
            level.volume for level in self.bids[:num_levels]
        )
        ask_volume = sum(
            level.volume for level in self.asks[:num_levels]
        )

        return {
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "total_volume": bid_volume + ask_volume,
            "ratio": bid_volume / (bid_volume + ask_volume) if (bid_volume + ask_volume) > 0 else 0.5
        }

    def get_price_levels(self, side: str, num_levels: int = 10) -> List[float]:
        """
        Get price levels for specified side

        Args:
            side: 'bid' or 'ask'
            num_levels: Number of levels to return

        Returns:
            List of prices
        """
        levels = self.bids if side.lower() == 'bid' else self.asks
        return [level.price for level in levels[:num_levels]]

    def find_support_resistance(
        self,
        num_levels: int = 10,
        volume_threshold: float = 0.2
    ) -> Dict[str, List[float]]:
        """
        Find potential support and resistance levels based on volume

        Args:
            num_levels: Number of levels to analyze
            volume_threshold: Minimum volume ratio to consider

        Returns:
            Dictionary with support and resistance levels
        """
        support_levels = []
        resistance_levels = []

        # Analyze bids for support
        bid_volumes = [level.volume for level in self.bids[:num_levels]]
        if bid_volumes:
            max_bid_volume = max(bid_volumes)
            for level in self.bids[:num_levels]:
                if level.volume >= max_bid_volume * volume_threshold:
                    support_levels.append(level.price)

        # Analyze asks for resistance
        ask_volumes = [level.volume for level in self.asks[:num_levels]]
        if ask_volumes:
            max_ask_volume = max(ask_volumes)
            for level in self.asks[:num_levels]:
                if level.volume >= max_ask_volume * volume_threshold:
                    resistance_levels.append(level.price)

        return {
            "support": support_levels,
            "resistance": resistance_levels
        }

    def detect_large_orders(
        self,
        num_levels: int = 10,
        threshold_ratio: float = 0.2
    ) -> Dict[str, List[OrderBookLevel]]:
        """
        Detect large orders in order book

        Args:
            num_levels: Number of levels to analyze
            threshold_ratio: Minimum volume ratio to consider large

        Returns:
            Dictionary with large bid and ask orders
        """
        # Calculate average volume
        bid_volumes = [level.volume for level in self.bids[:num_levels]]
        ask_volumes = [level.volume for level in self.asks[:num_levels]]

        avg_bid_volume = sum(bid_volumes) / len(bid_volumes) if bid_volumes else 0
        avg_ask_volume = sum(ask_volumes) / len(ask_volumes) if ask_volumes else 0

        total_avg = (avg_bid_volume + avg_ask_volume) / 2 if (avg_bid_volume + avg_ask_volume) > 0 else 0

        # Find large orders
        large_bids = [
            level for level in self.bids[:num_levels]
            if level.volume >= total_avg * (1 + threshold_ratio)
        ]

        large_asks = [
            level for level in self.asks[:num_levels]
            if level.volume >= total_avg * (1 + threshold_ratio)
        ]

        return {
            "large_bids": large_bids,
            "large_asks": large_asks,
            "bid_count": len(large_bids),
            "ask_count": len(large_asks)
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "best_bid": self.best_bid.to_dict() if self.best_bid else None,
            "best_ask": self.best_ask.to_dict() if self.best_ask else None,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "mid_price": self.mid_price,
            "total_bid_volume": self.total_bid_volume,
            "total_ask_volume": self.total_ask_volume,
            "bid_ask_ratio": self.bid_ask_volume_ratio
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderBook":
        """Create OrderBook from dictionary"""
        bids = [
            OrderBookLevel(
                price=level["price"],
                volume=level["volume"],
                orders_count=level.get("orders_count", 1)
            )
            for level in data.get("bids", [])
        ]

        asks = [
            OrderBookLevel(
                price=level["price"],
                volume=level["volume"],
                orders_count=level.get("orders_count", 1)
            )
            for level in data.get("asks", [])
        ]

        return cls(
            symbol=data.get("symbol", ""),
            bids=bids,
            asks=asks,
            timestamp=data.get("timestamp", int(datetime.utcnow().timestamp()))
        )

    @classmethod
    def from_api_response(cls, symbol: str, response: Dict[str, Any]) -> "OrderBook":
        """
        Create OrderBook from Match-Trade API response

        Args:
            symbol: Trading symbol
            response: API response data

        Returns:
            OrderBook instance
        """
        bids_data = response.get("bids", [])
        asks_data = response.get("asks", [])

        bids = [
            OrderBookLevel(
                price=float(item[0]) if isinstance(item, list) else float(item.get("price", 0)),
                volume=float(item[1]) if isinstance(item, list) else float(item.get("volume", 0)),
                orders_count=int(item[2]) if isinstance(item, list) and len(item) > 2 else 1
            )
            for item in bids_data
        ]

        asks = [
            OrderBookLevel(
                price=float(item[0]) if isinstance(item, list) else float(item.get("price", 0)),
                volume=float(item[1]) if isinstance(item, list) else float(item.get("volume", 0)),
                orders_count=int(item[2]) if isinstance(item, list) and len(item) > 2 else 1
            )
            for item in asks_data
        ]

        # Sort bids descending (highest price first)
        bids.sort(key=lambda x: x.price, reverse=True)

        # Sort asks ascending (lowest price first)
        asks.sort(key=lambda x: x.price)

        return cls(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=response.get("timestamp", int(datetime.utcnow().timestamp()))
        )


class OrderBookManager:
    """
    Manager for multiple order books
    Maintains order books for multiple symbols
    """

    def __init__(self):
        self.order_books: Dict[str, OrderBook] = {}
        self.logger = logger

    def update(self, symbol: str, order_book: OrderBook) -> None:
        """
        Update order book for symbol

        Args:
            symbol: Trading symbol
            order_book: OrderBook instance
        """
        self.order_books[symbol] = order_book
        self.logger.debug("Order book updated", symbol=symbol)

    def get(self, symbol: str) -> Optional[OrderBook]:
        """
        Get order book for symbol

        Args:
            symbol: Trading symbol

        Returns:
            OrderBook instance or None
        """
        return self.order_books.get(symbol)

    def get_all(self) -> Dict[str, OrderBook]:
        """Get all order books"""
        return self.order_books.copy()

    def clear(self) -> None:
        """Clear all order books"""
        self.order_books.clear()
        self.logger.info("All order books cleared")

    def get_symbols(self) -> List[str]:
        """Get list of symbols with order books"""
        return list(self.order_books.keys())
