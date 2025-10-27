"""
Unit tests for WebSocket client
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.websocket_client import (
    WebSocketClient,
    MarketDataWebSocket,
    ConnectionState
)


class TestConnectionState:
    """Tests for ConnectionState enum"""

    def test_connection_states(self):
        """Test connection state values"""
        assert ConnectionState.DISCONNECTED.value == "DISCONNECTED"
        assert ConnectionState.CONNECTING.value == "CONNECTING"
        assert ConnectionState.CONNECTED.value == "CONNECTED"
        assert ConnectionState.RECONNECTING.value == "RECONNECTING"
        assert ConnectionState.FAILED.value == "FAILED"


class TestWebSocketClient:
    """Tests for WebSocketClient"""

    @pytest.fixture
    def ws_client(self):
        """Create WebSocketClient instance"""
        return WebSocketClient(
            ws_url="ws://test.example.com/ws",
            token="test_token"
        )

    def test_initialization(self, ws_client):
        """Test WebSocket client initialization"""
        assert ws_client.ws_url == "ws://test.example.com/ws"
        assert ws_client.token == "test_token"
        assert ws_client.state == ConnectionState.DISCONNECTED
        assert ws_client.running is False
        assert ws_client.reconnect_attempts == 0
        assert ws_client.messages_received == 0
        assert ws_client.messages_sent == 0

    def test_is_connected(self, ws_client):
        """Test is_connected method"""
        # Initially not connected
        assert ws_client.is_connected() is False

        # Set to connected
        ws_client.state = ConnectionState.CONNECTED
        ws_client.websocket = MagicMock()
        assert ws_client.is_connected() is True

        # Set to connecting (not connected yet)
        ws_client.state = ConnectionState.CONNECTING
        assert ws_client.is_connected() is False

    def test_get_statistics(self, ws_client):
        """Test get_statistics method"""
        ws_client.messages_received = 100
        ws_client.messages_sent = 50
        ws_client.errors_count = 5
        ws_client.reconnect_attempts = 2
        ws_client.subscriptions = ["channel1:symbol1", "channel2:symbol2"]
        ws_client.connection_time = datetime.utcnow()

        stats = ws_client.get_statistics()

        assert stats["state"] == ConnectionState.DISCONNECTED.value
        assert stats["messages_received"] == 100
        assert stats["messages_sent"] == 50
        assert stats["errors_count"] == 5
        assert stats["reconnect_attempts"] == 2
        assert stats["subscriptions"] == 2
        assert "uptime_seconds" in stats

    @pytest.mark.asyncio
    async def test_send_when_not_connected(self, ws_client):
        """Test send fails when not connected"""
        result = await ws_client.send({"test": "data"})
        assert result is False

    @pytest.mark.asyncio
    async def test_subscribe(self, ws_client):
        """Test subscribe method"""
        ws_client.state = ConnectionState.CONNECTED
        ws_client.websocket = AsyncMock()
        ws_client.websocket.send = AsyncMock()

        await ws_client.subscribe("candles", ["BTCUSD"])

        # Check subscription was added
        assert len(ws_client.subscriptions) == 1
        assert "candles:BTCUSD" in ws_client.subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe(self, ws_client):
        """Test unsubscribe method"""
        ws_client.state = ConnectionState.CONNECTED
        ws_client.websocket = AsyncMock()
        ws_client.websocket.send = AsyncMock()
        ws_client.subscriptions = ["candles:BTCUSD"]

        await ws_client.unsubscribe("candles", ["BTCUSD"])

        # Check subscription was removed
        assert len(ws_client.subscriptions) == 0


class TestMarketDataWebSocket:
    """Tests for MarketDataWebSocket"""

    @pytest.fixture
    def market_ws(self):
        """Create MarketDataWebSocket instance"""
        return MarketDataWebSocket(
            token="test_token",
            trading_api_token="test_trading_token"
        )

    def test_initialization(self, market_ws):
        """Test MarketDataWebSocket initialization"""
        assert market_ws.token == "test_token"
        assert market_ws.trading_api_token == "test_trading_token"
        assert market_ws.client is not None
        assert len(market_ws.active_candle_subscriptions) == 0
        assert len(market_ws.active_orderbook_subscriptions) == 0

    @pytest.mark.asyncio
    async def test_handle_message_candle(self, market_ws):
        """Test handling candle message"""
        candle_data = {
            "type": "candle",
            "data": {
                "symbol": "BTCUSD",
                "close": 50000
            }
        }

        # Set callback
        callback_called = False
        received_data = None

        async def candle_callback(data):
            nonlocal callback_called, received_data
            callback_called = True
            received_data = data

        market_ws.candle_callback = candle_callback

        # Handle message
        await market_ws._handle_message(candle_data)

        assert callback_called is True
        assert received_data["symbol"] == "BTCUSD"

    @pytest.mark.asyncio
    async def test_handle_message_orderbook(self, market_ws):
        """Test handling orderbook message"""
        orderbook_data = {
            "type": "orderbook",
            "data": {
                "symbol": "BTCUSD",
                "bids": [[50000, 1.0]],
                "asks": [[50010, 1.2]]
            }
        }

        callback_called = False

        async def orderbook_callback(data):
            nonlocal callback_called
            callback_called = True

        market_ws.orderbook_callback = orderbook_callback

        await market_ws._handle_message(orderbook_data)

        assert callback_called is True

    @pytest.mark.asyncio
    async def test_handle_message_subscribed(self, market_ws):
        """Test handling subscription confirmation"""
        subscription_data = {
            "type": "subscribed",
            "channel": "candles"
        }

        # Should not raise error
        await market_ws._handle_message(subscription_data)

    @pytest.mark.asyncio
    async def test_handle_message_error(self, market_ws):
        """Test handling error message"""
        error_data = {
            "type": "error",
            "message": "Test error"
        }

        # Should not raise error
        await market_ws._handle_message(error_data)

    @pytest.mark.asyncio
    async def test_subscribe_candles(self, market_ws):
        """Test subscribing to candles"""
        market_ws.client.state = ConnectionState.CONNECTED
        market_ws.client.websocket = AsyncMock()
        market_ws.client.websocket.send = AsyncMock()

        callback_called = False

        async def callback(data):
            nonlocal callback_called
            callback_called = True

        await market_ws.subscribe_candles(
            symbols=["BTCUSD", "ETHUSD"],
            timeframe="1m",
            callback=callback
        )

        # Check subscriptions were added
        assert "BTCUSD" in market_ws.active_candle_subscriptions
        assert "ETHUSD" in market_ws.active_candle_subscriptions
        assert market_ws.active_candle_subscriptions["BTCUSD"]["timeframe"] == "1m"
        assert market_ws.candle_callback is not None

    @pytest.mark.asyncio
    async def test_unsubscribe_candles(self, market_ws):
        """Test unsubscribing from candles"""
        market_ws.client.state = ConnectionState.CONNECTED
        market_ws.client.websocket = AsyncMock()
        market_ws.client.websocket.send = AsyncMock()

        # Add subscriptions first
        market_ws.active_candle_subscriptions = {
            "BTCUSD": {"timeframe": "1m", "subscribed_at": datetime.utcnow()},
            "ETHUSD": {"timeframe": "1m", "subscribed_at": datetime.utcnow()}
        }

        await market_ws.unsubscribe_candles(["BTCUSD"])

        # Check subscription was removed
        assert "BTCUSD" not in market_ws.active_candle_subscriptions
        assert "ETHUSD" in market_ws.active_candle_subscriptions

    def test_get_statistics(self, market_ws):
        """Test get_statistics method"""
        market_ws.active_candle_subscriptions = {
            "BTCUSD": {"timeframe": "1m"},
            "ETHUSD": {"timeframe": "5m"}
        }
        market_ws.active_orderbook_subscriptions = ["BTCUSD"]
        market_ws.active_market_watch_subscriptions = ["BTCUSD", "ETHUSD"]

        stats = market_ws.get_statistics()

        assert stats["candle_subscriptions"] == 2
        assert stats["orderbook_subscriptions"] == 1
        assert stats["market_watch_subscriptions"] == 2
        assert "BTCUSD" in stats["candle_symbols"]
        assert "ETHUSD" in stats["candle_symbols"]

    def test_is_connected(self, market_ws):
        """Test is_connected method"""
        # Initially not connected
        assert market_ws.is_connected() is False

        # Mock connected state
        market_ws.client.state = ConnectionState.CONNECTED
        market_ws.client.websocket = MagicMock()

        assert market_ws.is_connected() is True

    @pytest.mark.asyncio
    async def test_wait_for_connection_success(self, market_ws):
        """Test wait_for_connection when connection succeeds"""
        # Simulate connection after short delay
        async def simulate_connect():
            await asyncio.sleep(0.2)
            market_ws.client.state = ConnectionState.CONNECTED
            market_ws.client.websocket = MagicMock()

        connect_task = asyncio.create_task(simulate_connect())

        result = await market_ws.wait_for_connection(timeout=1.0)

        await connect_task

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_connection_timeout(self, market_ws):
        """Test wait_for_connection timeout"""
        # Don't connect
        result = await market_ws.wait_for_connection(timeout=0.2)

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
