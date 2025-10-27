"""
Unit tests for OrderBook
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.orderbook import OrderBook, OrderBookLevel, OrderBookManager


class TestOrderBookLevel:
    """Tests for OrderBookLevel"""

    def test_level_creation(self):
        """Test order book level creation"""
        level = OrderBookLevel(
            price=50000,
            volume=1.5,
            orders_count=5
        )

        assert level.price == 50000
        assert level.volume == 1.5
        assert level.orders_count == 5

    def test_level_to_dict(self):
        """Test level to dictionary conversion"""
        level = OrderBookLevel(price=50000, volume=1.5)
        data = level.to_dict()

        assert data["price"] == 50000
        assert data["volume"] == 1.5


class TestOrderBook:
    """Tests for OrderBook"""

    @pytest.fixture
    def sample_orderbook(self):
        """Create sample order book"""
        bids = [
            OrderBookLevel(price=50000, volume=1.0),
            OrderBookLevel(price=49990, volume=2.0),
            OrderBookLevel(price=49980, volume=1.5),
        ]

        asks = [
            OrderBookLevel(price=50010, volume=1.2),
            OrderBookLevel(price=50020, volume=1.8),
            OrderBookLevel(price=50030, volume=2.5),
        ]

        return OrderBook(
            symbol="BTCUSD",
            bids=bids,
            asks=asks,
            timestamp=1234567890
        )

    def test_best_bid_ask(self, sample_orderbook):
        """Test best bid and ask"""
        assert sample_orderbook.best_bid.price == 50000
        assert sample_orderbook.best_ask.price == 50010

    def test_spread_calculation(self, sample_orderbook):
        """Test spread calculation"""
        assert sample_orderbook.spread == 10

    def test_spread_bps_calculation(self, sample_orderbook):
        """Test spread in basis points"""
        spread_bps = sample_orderbook.spread_bps
        assert spread_bps > 0

    def test_mid_price_calculation(self, sample_orderbook):
        """Test mid price calculation"""
        assert sample_orderbook.mid_price == 50005

    def test_total_volumes(self, sample_orderbook):
        """Test total volume calculations"""
        assert sample_orderbook.total_bid_volume == 4.5
        assert sample_orderbook.total_ask_volume == 5.5

    def test_bid_ask_ratio(self, sample_orderbook):
        """Test bid/ask volume ratio"""
        ratio = sample_orderbook.bid_ask_volume_ratio
        assert 0 <= ratio <= 1
        assert ratio == 4.5 / (4.5 + 5.5)

    def test_volume_at_levels(self, sample_orderbook):
        """Test volume at specific levels"""
        volumes = sample_orderbook.get_volume_at_levels(num_levels=2)

        assert volumes["bid_volume"] == 3.0  # 1.0 + 2.0
        assert volumes["ask_volume"] == 3.0  # 1.2 + 1.8

    def test_price_levels(self, sample_orderbook):
        """Test getting price levels"""
        bid_prices = sample_orderbook.get_price_levels("bid", num_levels=2)
        ask_prices = sample_orderbook.get_price_levels("ask", num_levels=2)

        assert bid_prices == [50000, 49990]
        assert ask_prices == [50010, 50020]

    def test_support_resistance(self, sample_orderbook):
        """Test support and resistance levels"""
        levels = sample_orderbook.find_support_resistance(
            num_levels=3,
            volume_threshold=0.5
        )

        assert "support" in levels
        assert "resistance" in levels
        assert isinstance(levels["support"], list)
        assert isinstance(levels["resistance"], list)

    def test_large_orders_detection(self, sample_orderbook):
        """Test large orders detection"""
        large_orders = sample_orderbook.detect_large_orders(
            num_levels=3,
            threshold_ratio=0.2
        )

        assert "large_bids" in large_orders
        assert "large_asks" in large_orders
        assert "bid_count" in large_orders
        assert "ask_count" in large_orders

    def test_to_dict(self, sample_orderbook):
        """Test converting order book to dictionary"""
        data = sample_orderbook.to_dict()

        assert data["symbol"] == "BTCUSD"
        assert "bids" in data
        assert "asks" in data
        assert "spread" in data
        assert "mid_price" in data

    def test_from_dict(self, sample_orderbook):
        """Test creating order book from dictionary"""
        data = sample_orderbook.to_dict()
        orderbook = OrderBook.from_dict(data)

        assert orderbook.symbol == sample_orderbook.symbol
        assert len(orderbook.bids) == len(sample_orderbook.bids)
        assert len(orderbook.asks) == len(sample_orderbook.asks)

    def test_from_api_response_array_format(self):
        """Test creating order book from API response (array format)"""
        response = {
            "bids": [
                [50000, 1.0, 5],
                [49990, 2.0, 3]
            ],
            "asks": [
                [50010, 1.2, 4],
                [50020, 1.8, 2]
            ],
            "timestamp": 1234567890
        }

        orderbook = OrderBook.from_api_response("BTCUSD", response)

        assert orderbook.symbol == "BTCUSD"
        assert len(orderbook.bids) == 2
        assert len(orderbook.asks) == 2
        assert orderbook.best_bid.price == 50000
        assert orderbook.best_ask.price == 50010

    def test_from_api_response_object_format(self):
        """Test creating order book from API response (object format)"""
        response = {
            "bids": [
                {"price": 50000, "volume": 1.0},
                {"price": 49990, "volume": 2.0}
            ],
            "asks": [
                {"price": 50010, "volume": 1.2},
                {"price": 50020, "volume": 1.8}
            ],
            "timestamp": 1234567890
        }

        orderbook = OrderBook.from_api_response("BTCUSD", response)

        assert orderbook.symbol == "BTCUSD"
        assert len(orderbook.bids) == 2
        assert len(orderbook.asks) == 2

    def test_empty_orderbook(self):
        """Test empty order book"""
        orderbook = OrderBook(symbol="BTCUSD", bids=[], asks=[])

        assert orderbook.best_bid is None
        assert orderbook.best_ask is None
        assert orderbook.spread == 0.0
        assert orderbook.total_bid_volume == 0.0


class TestOrderBookManager:
    """Tests for OrderBookManager"""

    @pytest.fixture
    def manager(self):
        """Create OrderBookManager instance"""
        return OrderBookManager()

    @pytest.fixture
    def sample_orderbook(self):
        """Create sample order book"""
        bids = [OrderBookLevel(price=50000, volume=1.0)]
        asks = [OrderBookLevel(price=50010, volume=1.2)]

        return OrderBook(
            symbol="BTCUSD",
            bids=bids,
            asks=asks
        )

    def test_update_orderbook(self, manager, sample_orderbook):
        """Test updating order book"""
        manager.update("BTCUSD", sample_orderbook)

        retrieved = manager.get("BTCUSD")
        assert retrieved is not None
        assert retrieved.symbol == "BTCUSD"

    def test_get_nonexistent_orderbook(self, manager):
        """Test getting non-existent order book"""
        orderbook = manager.get("NONEXISTENT")
        assert orderbook is None

    def test_get_all_orderbooks(self, manager, sample_orderbook):
        """Test getting all order books"""
        manager.update("BTCUSD", sample_orderbook)
        manager.update("ETHUSD", sample_orderbook)

        all_orderbooks = manager.get_all()
        assert len(all_orderbooks) == 2
        assert "BTCUSD" in all_orderbooks
        assert "ETHUSD" in all_orderbooks

    def test_clear_orderbooks(self, manager, sample_orderbook):
        """Test clearing all order books"""
        manager.update("BTCUSD", sample_orderbook)
        manager.update("ETHUSD", sample_orderbook)

        manager.clear()

        assert len(manager.get_all()) == 0
        assert manager.get("BTCUSD") is None

    def test_get_symbols(self, manager, sample_orderbook):
        """Test getting list of symbols"""
        manager.update("BTCUSD", sample_orderbook)
        manager.update("ETHUSD", sample_orderbook)

        symbols = manager.get_symbols()
        assert len(symbols) == 2
        assert "BTCUSD" in symbols
        assert "ETHUSD" in symbols


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
