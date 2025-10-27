"""
Match-Trade API Client

Handles all communication with Match-Trade Platform API
API Documentation: https://mtr-demo-prod.match-trader.com/docs
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MatchTradeAPIError(Exception):
    """Custom exception for Match-Trade API errors"""
    pass


class MatchTradeAPIClient:
    """
    Client for Match-Trade Platform API

    Handles authentication, market data, and trading operations
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client

        Args:
            base_url: Base URL for Match-Trade API
        """
        self.base_url = base_url or settings.API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def create_session(self):
        """Create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request payload
            headers: Custom headers
            max_retries: Maximum retry attempts

        Returns:
            Response data

        Raises:
            MatchTradeAPIError: If request fails
        """
        if not self.session:
            await self.create_session()

        url = f"{self.base_url}{endpoint}"
        request_headers = headers or {}

        for attempt in range(max_retries):
            try:
                async with self.session.request(
                    method,
                    url,
                    json=data,
                    headers=request_headers
                ) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        return response_data
                    elif response.status == 401:
                        raise MatchTradeAPIError(f"Unauthorized: {response_data}")
                    elif response.status == 400:
                        raise MatchTradeAPIError(f"Bad request: {response_data}")
                    elif response.status == 410:
                        raise MatchTradeAPIError(f"Resource expired: {response_data}")
                    else:
                        raise MatchTradeAPIError(
                            f"API error ({response.status}): {response_data}"
                        )

            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise MatchTradeAPIError(f"Network error: {str(e)}")

                # Exponential backoff
                wait_time = 2 ** attempt
                logger.warning(f"Request failed, retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)

            except Exception as e:
                raise MatchTradeAPIError(f"Unexpected error: {str(e)}")

    # ==================== AUTHENTICATION ====================

    async def login(
        self,
        email: str,
        password: str,
        broker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Login to Match-Trade platform

        Args:
            email: User email
            password: User password
            broker_id: Broker ID

        Returns:
            Session data including token and trading_api_token
        """
        try:
            response = await self._request(
                "POST",
                "/manager/mtr-login",
                data={
                    "email": email,
                    "password": password,
                    "brokerId": broker_id or settings.MATCH_TRADE_BROKER_ID
                }
            )

            logger.info(f"Login successful for user: {email}")
            return response

        except Exception as e:
            logger.error(f"Login failed for {email}: {e}")
            raise

    async def refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Refresh authentication token

        Args:
            token: Current authentication token

        Returns:
            New session data
        """
        try:
            response = await self._request(
                "POST",
                "/manager/refresh-token",
                headers={"Authorization": f"Bearer {token}"}
            )

            logger.info("Token refreshed successfully")
            return response

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise

    async def logout(self, token: str) -> bool:
        """
        Logout from Match-Trade platform

        Args:
            token: Authentication token

        Returns:
            True if successful
        """
        try:
            await self._request(
                "POST",
                "/manager/logout",
                headers={"Authorization": f"Bearer {token}"}
            )

            logger.info("Logout successful")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    # ==================== ACCOUNT INFORMATION ====================

    async def get_balance(
        self,
        token: str,
        trading_api_token: str
    ) -> Dict[str, Any]:
        """
        Get account balance information

        Args:
            token: Authentication token
            trading_api_token: Trading API token

        Returns:
            Balance information
        """
        try:
            response = await self._request(
                "GET",
                "/trading/balance",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response

        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise

    async def get_platform_details(self, token: str) -> Dict[str, Any]:
        """
        Get platform details

        Args:
            token: Authentication token

        Returns:
            Platform details
        """
        try:
            response = await self._request(
                "GET",
                "/manager/platform",
                headers={"Authorization": f"Bearer {token}"}
            )

            return response

        except Exception as e:
            logger.error(f"Failed to get platform details: {e}")
            raise

    # ==================== MARKET DATA ====================

    async def get_market_watch(
        self,
        token: str,
        trading_api_token: str
    ) -> List[Dict[str, Any]]:
        """
        Get market watch data (real-time prices)

        Args:
            token: Authentication token
            trading_api_token: Trading API token

        Returns:
            List of market watch data
        """
        try:
            response = await self._request(
                "GET",
                "/trading/market-watch",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response if isinstance(response, list) else response.get("data", [])

        except Exception as e:
            logger.error(f"Failed to get market watch: {e}")
            raise

    async def get_symbols(
        self,
        token: str,
        trading_api_token: str
    ) -> List[Dict[str, Any]]:
        """
        Get available trading symbols

        Args:
            token: Authentication token
            trading_api_token: Trading API token

        Returns:
            List of symbols
        """
        try:
            response = await self._request(
                "GET",
                "/trading/symbols",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response if isinstance(response, list) else response.get("data", [])

        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
            raise

    async def get_candles(
        self,
        token: str,
        trading_api_token: str,
        symbol: str,
        timeframe: str = "1",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get candlestick data

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            symbol: Trading symbol
            timeframe: Timeframe (1, 5, 15, 30, 60, etc.)
            limit: Number of candles to retrieve

        Returns:
            List of candles
        """
        try:
            response = await self._request(
                "GET",
                f"/trading/candles?symbol={symbol}&timeframe={timeframe}&limit={limit}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response if isinstance(response, list) else response.get("data", [])

        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            raise

    # ==================== POSITION MANAGEMENT ====================

    async def get_opened_positions(
        self,
        token: str,
        trading_api_token: str
    ) -> List[Dict[str, Any]]:
        """
        Get all opened positions

        Args:
            token: Authentication token
            trading_api_token: Trading API token

        Returns:
            List of opened positions
        """
        try:
            response = await self._request(
                "GET",
                "/trading/positions/opened",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response if isinstance(response, list) else response.get("data", [])

        except Exception as e:
            logger.error(f"Failed to get opened positions: {e}")
            raise

    async def open_position(
        self,
        token: str,
        trading_api_token: str,
        symbol: str,
        side: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Open a new position

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            symbol: Trading symbol
            side: BUY or SELL
            volume: Position volume
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Position data
        """
        try:
            data = {
                "symbol": symbol,
                "side": side,
                "volume": volume
            }

            if stop_loss:
                data["stopLoss"] = stop_loss
            if take_profit:
                data["takeProfit"] = take_profit

            response = await self._request(
                "POST",
                "/trading/positions/open",
                data=data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            logger.info(f"Position opened: {symbol} {side} {volume}")
            return response

        except Exception as e:
            logger.error(f"Failed to open position {symbol}: {e}")
            raise

    async def close_position(
        self,
        token: str,
        trading_api_token: str,
        position_id: str
    ) -> Dict[str, Any]:
        """
        Close a position

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            position_id: Position ID to close

        Returns:
            Close result
        """
        try:
            response = await self._request(
                "POST",
                f"/trading/positions/{position_id}/close",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            logger.info(f"Position closed: {position_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            raise

    async def edit_position(
        self,
        token: str,
        trading_api_token: str,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Edit position stop loss and take profit

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            position_id: Position ID
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            Updated position data
        """
        try:
            data = {}
            if stop_loss is not None:
                data["stopLoss"] = stop_loss
            if take_profit is not None:
                data["takeProfit"] = take_profit

            response = await self._request(
                "PUT",
                f"/trading/positions/{position_id}",
                data=data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            logger.info(f"Position edited: {position_id}")
            return response

        except Exception as e:
            logger.error(f"Failed to edit position {position_id}: {e}")
            raise

    async def partial_close(
        self,
        token: str,
        trading_api_token: str,
        position_id: str,
        volume: float
    ) -> Dict[str, Any]:
        """
        Partially close a position

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            position_id: Position ID
            volume: Volume to close

        Returns:
            Updated position data
        """
        try:
            response = await self._request(
                "POST",
                f"/trading/positions/{position_id}/partial-close",
                data={"volume": volume},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            logger.info(f"Position partially closed: {position_id}, volume: {volume}")
            return response

        except Exception as e:
            logger.error(f"Failed to partially close position {position_id}: {e}")
            raise

    async def get_closed_positions(
        self,
        token: str,
        trading_api_token: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get closed positions

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            from_date: Start date filter
            to_date: End date filter

        Returns:
            List of closed positions
        """
        try:
            params = []
            if from_date:
                params.append(f"fromDate={from_date.isoformat()}")
            if to_date:
                params.append(f"toDate={to_date.isoformat()}")

            query_string = "?" + "&".join(params) if params else ""

            response = await self._request(
                "GET",
                f"/trading/positions/closed{query_string}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response if isinstance(response, list) else response.get("data", [])

        except Exception as e:
            logger.error(f"Failed to get closed positions: {e}")
            raise

    # ==================== ORDER MANAGEMENT ====================

    async def get_active_orders(
        self,
        token: str,
        trading_api_token: str
    ) -> List[Dict[str, Any]]:
        """
        Get active pending orders

        Args:
            token: Authentication token
            trading_api_token: Trading API token

        Returns:
            List of active orders
        """
        try:
            response = await self._request(
                "GET",
                "/trading/orders/active",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            return response if isinstance(response, list) else response.get("data", [])

        except Exception as e:
            logger.error(f"Failed to get active orders: {e}")
            raise

    async def create_pending_order(
        self,
        token: str,
        trading_api_token: str,
        symbol: str,
        side: str,
        volume: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a pending order

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            symbol: Trading symbol
            side: BUY or SELL
            volume: Order volume
            price: Order price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Order data
        """
        try:
            data = {
                "symbol": symbol,
                "side": side,
                "volume": volume,
                "price": price
            }

            if stop_loss:
                data["stopLoss"] = stop_loss
            if take_profit:
                data["takeProfit"] = take_profit

            response = await self._request(
                "POST",
                "/trading/orders/pending",
                data=data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            logger.info(f"Pending order created: {symbol} {side} {volume} @ {price}")
            return response

        except Exception as e:
            logger.error(f"Failed to create pending order {symbol}: {e}")
            raise

    async def cancel_pending_order(
        self,
        token: str,
        trading_api_token: str,
        order_id: str
    ) -> bool:
        """
        Cancel a pending order

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            order_id: Order ID to cancel

        Returns:
            True if successful
        """
        try:
            await self._request(
                "DELETE",
                f"/trading/orders/{order_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Trading-Api-Token": trading_api_token
                }
            )

            logger.info(f"Pending order cancelled: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
