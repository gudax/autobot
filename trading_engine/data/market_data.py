"""
Market Data Collector for Match-Trade Platform
Collects real-time market data including candles, symbols, and market watch data
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
from config import settings
from utils.logger import get_logger


logger = get_logger("market_data")


@dataclass
class Candle:
    """Candle data structure"""
    symbol: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    timeframe: str = "1m"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
            "timeframe": self.timeframe
        }


@dataclass
class Symbol:
    """Symbol information"""
    symbol: str
    name: str
    description: str = ""
    base_currency: str = ""
    quote_currency: str = ""
    min_volume: float = 0.01
    max_volume: float = 100.0
    tick_size: float = 0.01
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "description": self.description,
            "base_currency": self.base_currency,
            "quote_currency": self.quote_currency,
            "min_volume": self.min_volume,
            "max_volume": self.max_volume,
            "tick_size": self.tick_size,
            "is_active": self.is_active
        }


@dataclass
class MarketTick:
    """Market tick data"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: float
    timestamp: int
    change_percent: float = 0.0

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        return self.ask - self.bid

    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        return (self.bid + self.ask) / 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "change_percent": self.change_percent,
            "spread": self.spread,
            "mid_price": self.mid_price
        }


class MarketDataCache:
    """Cache for market data with TTL"""

    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}

    def set(self, key: str, value: Any) -> None:
        """Set cache value"""
        self._cache[key] = value
        self._timestamps[key] = datetime.utcnow()

    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        if key not in self._cache:
            return None

        timestamp = self._timestamps[key]
        if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl):
            # Expired
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            return None

        return self._cache[key]

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()

    def remove(self, key: str) -> None:
        """Remove specific cache entry"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)


class MarketDataCollector:
    """
    Market Data Collector for Match-Trade Platform
    Collects real-time market data via REST API
    """

    def __init__(
        self,
        token: Optional[str] = None,
        trading_api_token: Optional[str] = None,
        cache_enabled: bool = True
    ):
        self.base_url = settings.api_base_url
        self.token = token
        self.trading_api_token = trading_api_token
        self.timeout = aiohttp.ClientTimeout(total=settings.api_timeout)
        self.logger = logger

        # Cache
        self.cache_enabled = cache_enabled
        self.cache = MarketDataCache(ttl=settings.cache_ttl)

        # Session
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        use_trading_token: bool = False
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Match-Trade API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            use_trading_token: Use trading API token instead of regular token

        Returns:
            API response data

        Raises:
            Exception: If request fails
        """
        await self._ensure_session()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Use trading token if specified
        if use_trading_token and self.trading_api_token:
            headers["TradingApiToken"] = self.trading_api_token

        try:
            async with self._session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers
            ) as response:
                response_data = await response.json()

                if response.status >= 400:
                    self.logger.error(
                        "API request failed",
                        status=response.status,
                        endpoint=endpoint,
                        response=response_data
                    )
                    raise Exception(f"API error: {response.status} - {response_data}")

                return response_data

        except aiohttp.ClientError as e:
            self.logger.error("HTTP client error", error=str(e), endpoint=endpoint)
            raise
        except Exception as e:
            self.logger.error("Request error", error=str(e), endpoint=endpoint)
            raise

    async def get_symbols(self, use_cache: bool = True) -> List[Symbol]:
        """
        Get list of available trading symbols

        Args:
            use_cache: Use cached data if available

        Returns:
            List of Symbol objects
        """
        cache_key = "symbols"

        if use_cache and self.cache_enabled:
            cached = self.cache.get(cache_key)
            if cached:
                self.logger.debug("Using cached symbols")
                return cached

        try:
            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/symbols",
                use_trading_token=True
            )

            symbols = []
            for item in response.get("data", []):
                symbol = Symbol(
                    symbol=item.get("symbol", ""),
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    base_currency=item.get("baseCurrency", ""),
                    quote_currency=item.get("quoteCurrency", ""),
                    min_volume=float(item.get("minVolume", 0.01)),
                    max_volume=float(item.get("maxVolume", 100)),
                    tick_size=float(item.get("tickSize", 0.01)),
                    is_active=item.get("isActive", True)
                )
                symbols.append(symbol)

            if self.cache_enabled:
                self.cache.set(cache_key, symbols)

            self.logger.info("Fetched symbols", count=len(symbols))
            return symbols

        except Exception as e:
            self.logger.error("Failed to fetch symbols", error=str(e))
            raise

    async def get_market_watch(
        self,
        symbols: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> List[MarketTick]:
        """
        Get real-time market watch data

        Args:
            symbols: List of symbols to fetch (None = all)
            use_cache: Use cached data if available

        Returns:
            List of MarketTick objects
        """
        cache_key = f"market_watch_{','.join(symbols) if symbols else 'all'}"

        if use_cache and self.cache_enabled:
            cached = self.cache.get(cache_key)
            if cached:
                self.logger.debug("Using cached market watch")
                return cached

        try:
            params = {}
            if symbols:
                params["symbols"] = ",".join(symbols)

            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/market-watch",
                params=params,
                use_trading_token=True
            )

            ticks = []
            for item in response.get("data", []):
                tick = MarketTick(
                    symbol=item.get("symbol", ""),
                    bid=float(item.get("bid", 0)),
                    ask=float(item.get("ask", 0)),
                    last=float(item.get("last", 0)),
                    volume=float(item.get("volume", 0)),
                    timestamp=item.get("timestamp", int(datetime.utcnow().timestamp())),
                    change_percent=float(item.get("changePercent", 0))
                )
                ticks.append(tick)

            if self.cache_enabled:
                self.cache.set(cache_key, ticks)

            self.logger.info("Fetched market watch", count=len(ticks))
            return ticks

        except Exception as e:
            self.logger.error("Failed to fetch market watch", error=str(e))
            raise

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 100,
        use_cache: bool = True
    ) -> List[Candle]:
        """
        Get historical candle data

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
            use_cache: Use cached data if available

        Returns:
            List of Candle objects
        """
        cache_key = f"candles_{symbol}_{timeframe}_{limit}"

        if use_cache and self.cache_enabled:
            cached = self.cache.get(cache_key)
            if cached:
                self.logger.debug("Using cached candles", symbol=symbol, timeframe=timeframe)
                return cached

        try:
            params = {
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit
            }

            response = await self._make_request(
                method="GET",
                endpoint="/api/v1/candles",
                params=params,
                use_trading_token=True
            )

            candles = []
            for item in response.get("data", []):
                candle = Candle(
                    symbol=symbol,
                    timestamp=item.get("timestamp", 0),
                    open=float(item.get("open", 0)),
                    high=float(item.get("high", 0)),
                    low=float(item.get("low", 0)),
                    close=float(item.get("close", 0)),
                    volume=float(item.get("volume", 0)),
                    buy_volume=float(item.get("buyVolume", 0)),
                    sell_volume=float(item.get("sellVolume", 0)),
                    timeframe=timeframe
                )
                candles.append(candle)

            if self.cache_enabled:
                self.cache.set(cache_key, candles)

            self.logger.info(
                "Fetched candles",
                symbol=symbol,
                timeframe=timeframe,
                count=len(candles)
            )
            return candles

        except Exception as e:
            self.logger.error(
                "Failed to fetch candles",
                symbol=symbol,
                timeframe=timeframe,
                error=str(e)
            )
            raise

    async def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get latest price for symbol

        Args:
            symbol: Trading symbol

        Returns:
            Latest price or None if not available
        """
        try:
            ticks = await self.get_market_watch(symbols=[symbol])
            if ticks:
                return ticks[0].last
            return None
        except Exception as e:
            self.logger.error("Failed to get latest price", symbol=symbol, error=str(e))
            return None

    async def subscribe_realtime(self, symbols: List[str]):
        """
        Subscribe to real-time data (placeholder for WebSocket implementation)

        Args:
            symbols: List of symbols to subscribe
        """
        # TODO: Implement WebSocket subscription
        self.logger.info("Real-time subscription requested", symbols=symbols)
        raise NotImplementedError("WebSocket subscription not yet implemented")

    def clear_cache(self):
        """Clear all cached data"""
        if self.cache_enabled:
            self.cache.clear()
            self.logger.info("Cache cleared")
