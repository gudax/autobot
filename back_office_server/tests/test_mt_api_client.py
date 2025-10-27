"""
Unit tests for Match-Trade API Client
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp

from app.services.mt_api_client import MatchTradeAPIClient, MatchTradeAPIError


class TestMatchTradeAPIClient:
    """Tests for MatchTradeAPIClient"""

    @pytest.fixture
    def api_client(self):
        """Create API client instance"""
        return MatchTradeAPIClient(base_url="https://test.example.com")

    @pytest.mark.asyncio
    async def test_initialization(self, api_client):
        """Test API client initialization"""
        assert api_client.base_url == "https://test.example.com"
        assert api_client.session is None

    @pytest.mark.asyncio
    async def test_create_session(self, api_client):
        """Test session creation"""
        await api_client.create_session()
        assert api_client.session is not None
        assert isinstance(api_client.session, aiohttp.ClientSession)
        await api_client.close()

    @pytest.mark.asyncio
    async def test_close_session(self, api_client):
        """Test session closure"""
        await api_client.create_session()
        await api_client.close()
        assert api_client.session is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        async with MatchTradeAPIClient() as client:
            assert client.session is not None
        # Session should be closed after context exit
        assert client.session is None

    @pytest.mark.asyncio
    async def test_login_success(self, api_client):
        """Test successful login"""
        mock_response = {
            "token": "test_token",
            "trading_api_token": "test_trading_token",
            "user": {"email": "test@example.com"}
        }

        with patch.object(api_client, '_request', new=AsyncMock(return_value=mock_response)):
            result = await api_client.login("test@example.com", "password123")

            assert result["token"] == "test_token"
            assert result["trading_api_token"] == "test_trading_token"

    @pytest.mark.asyncio
    async def test_login_failure(self, api_client):
        """Test login failure"""
        with patch.object(api_client, '_request', new=AsyncMock(side_effect=MatchTradeAPIError("Login failed"))):
            with pytest.raises(MatchTradeAPIError):
                await api_client.login("test@example.com", "wrong_password")

    @pytest.mark.asyncio
    async def test_get_market_watch(self, api_client):
        """Test get market watch"""
        mock_data = [
            {"symbol": "BTCUSD", "bid": 50000, "ask": 50010},
            {"symbol": "ETHUSD", "bid": 3000, "ask": 3005}
        ]

        with patch.object(api_client, '_request', new=AsyncMock(return_value=mock_data)):
            result = await api_client.get_market_watch("token", "trading_token")

            assert len(result) == 2
            assert result[0]["symbol"] == "BTCUSD"

    @pytest.mark.asyncio
    async def test_open_position(self, api_client):
        """Test open position"""
        mock_position = {
            "id": "pos_123",
            "symbol": "BTCUSD",
            "side": "BUY",
            "volume": 0.1,
            "entry_price": 50000
        }

        with patch.object(api_client, '_request', new=AsyncMock(return_value=mock_position)):
            result = await api_client.open_position(
                "token",
                "trading_token",
                "BTCUSD",
                "BUY",
                0.1,
                stop_loss=49900,
                take_profit=50150
            )

            assert result["id"] == "pos_123"
            assert result["symbol"] == "BTCUSD"

    @pytest.mark.asyncio
    async def test_close_position(self, api_client):
        """Test close position"""
        mock_result = {
            "success": True,
            "position_id": "pos_123",
            "profit_loss": 15.5
        }

        with patch.object(api_client, '_request', new=AsyncMock(return_value=mock_result)):
            result = await api_client.close_position("token", "trading_token", "pos_123")

            assert result["success"] is True
            assert result["profit_loss"] == 15.5

    @pytest.mark.asyncio
    async def test_get_balance(self, api_client):
        """Test get balance"""
        mock_balance = {
            "balance": 10000.0,
            "equity": 10150.5,
            "margin": 500.0,
            "free_margin": 9650.5
        }

        with patch.object(api_client, '_request', new=AsyncMock(return_value=mock_balance)):
            result = await api_client.get_balance("token", "trading_token")

            assert result["balance"] == 10000.0
            assert result["equity"] == 10150.5

    @pytest.mark.asyncio
    async def test_request_retry_on_network_error(self, api_client):
        """Test request retry on network error"""
        await api_client.create_session()

        # Mock session to raise ClientError on first two attempts, succeed on third
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientError("Network error")

            # Create mock response for successful attempt
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"success": True})
            return mock_response

        with patch.object(api_client.session, 'request', side_effect=mock_request):
            # This should succeed after retries
            result = await api_client._request("GET", "/test", max_retries=3)
            assert result["success"] is True
            assert call_count == 3

        await api_client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
