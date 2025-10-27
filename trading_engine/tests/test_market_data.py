"""
Unit tests for Market Data Collector
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.market_data import (
    MarketDataCollector,
    Candle,
    Symbol,
    MarketTick,
    MarketDataCache
)


class TestMarketDataCache:
    """Tests for MarketDataCache"""

    def test_set_and_get(self):
        """Test setting and getting cache values"""
        cache = MarketDataCache(ttl=60)

        # Set value
        cache.set("test_key", {"data": "test"})

        # Get value
        value = cache.get("test_key")
        assert value == {"data": "test"}

    def test_cache_expiration(self):
        """Test cache expiration"""
        cache = MarketDataCache(ttl=0)  # Immediate expiration

        cache.set("test_key", {"data": "test"})

        # Wait for expiration
        import time
        time.sleep(0.1)

        value = cache.get("test_key")
        assert value is None

    def test_clear_cache(self):
        """Test clearing cache"""
        cache = MarketDataCache(ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_remove_specific_key(self):
        """Test removing specific cache entry"""
        cache = MarketDataCache(ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.remove("key1")

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestCandle:
    """Tests for Candle data structure"""

    def test_candle_creation(self):
        """Test candle creation"""
        candle = Candle(
            symbol="BTCUSD",
            timestamp=1234567890,
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=1234.56,
            buy_volume=650.0,
            sell_volume=584.56,
            timeframe="1m"
        )

        assert candle.symbol == "BTCUSD"
        assert candle.open == 50000
        assert candle.close == 50050

    def test_candle_to_dict(self):
        """Test candle to dictionary conversion"""
        candle = Candle(
            symbol="BTCUSD",
            timestamp=1234567890,
            open=50000,
            high=50100,
            low=49900,
            close=50050,
            volume=1234.56,
            timeframe="1m"
        )

        data = candle.to_dict()

        assert data["symbol"] == "BTCUSD"
        assert data["open"] == 50000
        assert data["volume"] == 1234.56


class TestSymbol:
    """Tests for Symbol data structure"""

    def test_symbol_creation(self):
        """Test symbol creation"""
        symbol = Symbol(
            symbol="BTCUSD",
            name="Bitcoin vs US Dollar",
            base_currency="BTC",
            quote_currency="USD",
            min_volume=0.01,
            max_volume=100.0,
            tick_size=0.01
        )

        assert symbol.symbol == "BTCUSD"
        assert symbol.base_currency == "BTC"
        assert symbol.quote_currency == "USD"

    def test_symbol_to_dict(self):
        """Test symbol to dictionary conversion"""
        symbol = Symbol(
            symbol="BTCUSD",
            name="Bitcoin vs US Dollar"
        )

        data = symbol.to_dict()

        assert data["symbol"] == "BTCUSD"
        assert data["name"] == "Bitcoin vs US Dollar"


class TestMarketTick:
    """Tests for MarketTick data structure"""

    def test_market_tick_creation(self):
        """Test market tick creation"""
        tick = MarketTick(
            symbol="BTCUSD",
            bid=50000,
            ask=50010,
            last=50005,
            volume=1234.56,
            timestamp=1234567890,
            change_percent=0.5
        )

        assert tick.symbol == "BTCUSD"
        assert tick.bid == 50000
        assert tick.ask == 50010

    def test_spread_calculation(self):
        """Test spread calculation"""
        tick = MarketTick(
            symbol="BTCUSD",
            bid=50000,
            ask=50010,
            last=50005,
            volume=1234.56,
            timestamp=1234567890
        )

        assert tick.spread == 10

    def test_mid_price_calculation(self):
        """Test mid price calculation"""
        tick = MarketTick(
            symbol="BTCUSD",
            bid=50000,
            ask=50010,
            last=50005,
            volume=1234.56,
            timestamp=1234567890
        )

        assert tick.mid_price == 50005


class TestMarketDataCollector:
    """Tests for MarketDataCollector"""

    @pytest.fixture
    def collector(self):
        """Create MarketDataCollector instance"""
        return MarketDataCollector(
            token="test_token",
            trading_api_token="test_trading_token",
            cache_enabled=True
        )

    @pytest.mark.asyncio
    async def test_initialization(self, collector):
        """Test collector initialization"""
        assert collector.token == "test_token"
        assert collector.trading_api_token == "test_trading_token"
        assert collector.cache_enabled is True
        assert collector.cache is not None

    @pytest.mark.asyncio
    async def test_session_creation(self, collector):
        """Test session creation"""
        async with collector:
            assert collector._session is not None
            assert not collector._session.closed

    @pytest.mark.asyncio
    async def test_get_symbols_with_cache(self, collector):
        """Test get_symbols with caching"""
        # Mock API response
        mock_response = {
            "data": [
                {
                    "symbol": "BTCUSD",
                    "name": "Bitcoin vs US Dollar",
                    "baseCurrency": "BTC",
                    "quoteCurrency": "USD",
                    "minVolume": 0.01,
                    "maxVolume": 100.0,
                    "tickSize": 0.01,
                    "isActive": True
                }
            ]
        }

        # Mock the _make_request method
        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with collector:
                # First call - should hit API
                symbols = await collector.get_symbols(use_cache=True)
                assert len(symbols) == 1
                assert symbols[0].symbol == "BTCUSD"
                assert symbols[0].base_currency == "BTC"

                # Second call - should use cache
                symbols2 = await collector.get_symbols(use_cache=True)
                assert len(symbols2) == 1

                # Verify API was only called once (cache was used)
                assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_get_symbols_without_cache(self, collector):
        """Test get_symbols without cache"""
        mock_response = {
            "data": [
                {
                    "symbol": "ETHUSD",
                    "name": "Ethereum vs US Dollar",
                    "baseCurrency": "ETH",
                    "quoteCurrency": "USD",
                    "minVolume": 0.01,
                    "maxVolume": 100.0,
                    "tickSize": 0.01,
                    "isActive": True
                }
            ]
        }

        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with collector:
                symbols = await collector.get_symbols(use_cache=False)
                assert len(symbols) == 1
                assert symbols[0].symbol == "ETHUSD"

    @pytest.mark.asyncio
    async def test_get_market_watch(self, collector):
        """Test get_market_watch"""
        # Mock API response
        mock_response = {
            "data": [
                {
                    "symbol": "BTCUSD",
                    "bid": 50000,
                    "ask": 50010,
                    "last": 50005,
                    "volume": 1234.56,
                    "timestamp": 1234567890,
                    "changePercent": 0.5
                }
            ]
        }

        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with collector:
                ticks = await collector.get_market_watch(symbols=["BTCUSD"], use_cache=False)
                assert len(ticks) == 1
                assert ticks[0].symbol == "BTCUSD"
                assert ticks[0].bid == 50000
                assert ticks[0].ask == 50010
                assert ticks[0].spread == 10

    @pytest.mark.asyncio
    async def test_get_candles(self, collector):
        """Test get_candles"""
        # Mock API response
        mock_response = {
            "data": [
                {
                    "timestamp": 1234567890,
                    "open": 50000,
                    "high": 50100,
                    "low": 49900,
                    "close": 50050,
                    "volume": 1234.56,
                    "buyVolume": 650.0,
                    "sellVolume": 584.56
                }
            ]
        }

        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with collector:
                candles = await collector.get_candles(
                    symbol="BTCUSD",
                    timeframe="1m",
                    limit=100,
                    use_cache=False
                )
                assert len(candles) == 1
                assert candles[0].symbol == "BTCUSD"
                assert candles[0].open == 50000
                assert candles[0].close == 50050
                assert candles[0].volume == 1234.56

    @pytest.mark.asyncio
    async def test_get_latest_price(self, collector):
        """Test get_latest_price"""
        # Mock API response
        mock_response = {
            "data": [
                {
                    "symbol": "BTCUSD",
                    "bid": 50000,
                    "ask": 50010,
                    "last": 50005,
                    "volume": 1234.56,
                    "timestamp": 1234567890,
                    "changePercent": 0.5
                }
            ]
        }

        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with collector:
                price = await collector.get_latest_price("BTCUSD")
                assert price == 50005

    @pytest.mark.asyncio
    async def test_get_latest_price_no_data(self, collector):
        """Test get_latest_price when no data available"""
        mock_response = {"data": []}

        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            async with collector:
                price = await collector.get_latest_price("BTCUSD")
                assert price is None

    @pytest.mark.asyncio
    async def test_error_handling(self, collector):
        """Test error handling"""
        # Mock API error
        with patch.object(collector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("API Error")

            async with collector:
                with pytest.raises(Exception) as exc_info:
                    await collector.get_symbols(use_cache=False)

                assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_headers_generation(self, collector):
        """Test header generation"""
        headers = collector._get_headers()

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"

    def test_cache_clear(self, collector):
        """Test cache clearing"""
        collector.cache.set("test", "value")
        assert collector.cache.get("test") == "value"

        collector.clear_cache()
        assert collector.cache.get("test") is None

    @pytest.mark.asyncio
    async def test_close_session(self, collector):
        """Test closing session"""
        async with collector:
            assert collector._session is not None

        # Session should be closed after context exit
        assert collector._session.closed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
