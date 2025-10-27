"""
WebSocket client for real-time market data
"""

import asyncio
import json
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from enum import Enum
import websockets
from websockets.client import WebSocketClientProtocol
from config import settings
from utils.logger import get_logger


logger = get_logger("websocket")


class ConnectionState(str, Enum):
    """WebSocket connection state"""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"


class WebSocketClient:
    """
    WebSocket client for real-time data streaming
    """

    def __init__(
        self,
        ws_url: str,
        token: Optional[str] = None,
        on_message: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None
    ):
        """
        Initialize WebSocket client

        Args:
            ws_url: WebSocket URL
            token: Authentication token
            on_message: Callback for messages
            on_error: Callback for errors
            on_connect: Callback for connection
            on_disconnect: Callback for disconnection
        """
        self.ws_url = ws_url
        self.token = token
        self.on_message = on_message
        self.on_error = on_error
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self.websocket: Optional[WebSocketClientProtocol] = None
        self.running = False
        self.state = ConnectionState.DISCONNECTED
        self.subscriptions: List[str] = []

        # Reconnection settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = settings.ws_reconnect_attempts
        self.base_reconnect_delay = settings.ws_reconnect_delay

        # Statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.errors_count = 0
        self.last_message_time: Optional[datetime] = None
        self.connection_time: Optional[datetime] = None

        # Message queue for reliability
        self.message_queue: asyncio.Queue = asyncio.Queue()

        self.logger = logger

    async def connect(self) -> bool:
        """
        Connect to WebSocket server

        Returns:
            True if connected successfully
        """
        try:
            self.state = ConnectionState.CONNECTING
            self.logger.info("Connecting to WebSocket", url=self.ws_url)

            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=settings.ws_ping_interval,
                ping_timeout=10,
                close_timeout=5
            )

            self.running = True
            self.state = ConnectionState.CONNECTED
            self.reconnect_attempts = 0
            self.connection_time = datetime.utcnow()

            self.logger.info(
                "WebSocket connected successfully",
                url=self.ws_url,
                state=self.state.value
            )

            if self.on_connect:
                await self.on_connect()

            return True

        except Exception as e:
            self.state = ConnectionState.FAILED
            self.errors_count += 1
            self.logger.error(
                "WebSocket connection failed",
                error=str(e),
                attempt=self.reconnect_attempts,
                state=self.state.value
            )
            if self.on_error:
                await self.on_error(e)
            return False

    async def disconnect(self):
        """Disconnect from WebSocket server"""
        self.running = False
        self.state = ConnectionState.DISCONNECTED

        if self.websocket:
            try:
                await self.websocket.close()
                self.logger.info(
                    "WebSocket disconnected",
                    messages_received=self.messages_received,
                    messages_sent=self.messages_sent,
                    errors=self.errors_count
                )
            except Exception as e:
                self.logger.error("Error during disconnect", error=str(e))

        if self.on_disconnect:
            await self.on_disconnect()

    async def send(self, data: Dict[str, Any]) -> bool:
        """
        Send message to WebSocket

        Args:
            data: Message data

        Returns:
            True if sent successfully
        """
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            self.logger.error(
                "Cannot send message - WebSocket not connected",
                state=self.state.value
            )
            return False

        try:
            message = json.dumps(data)
            await self.websocket.send(message)
            self.messages_sent += 1
            self.logger.debug("Message sent", data=data, total_sent=self.messages_sent)
            return True

        except Exception as e:
            self.errors_count += 1
            self.logger.error("Failed to send message", error=str(e), errors=self.errors_count)
            if self.on_error:
                await self.on_error(e)
            return False

    async def subscribe(self, channel: str, symbols: Optional[List[str]] = None):
        """
        Subscribe to channel

        Args:
            channel: Channel name (e.g., 'candles', 'orderbook', 'trades')
            symbols: List of symbols to subscribe
        """
        subscription = {
            "action": "subscribe",
            "channel": channel
        }

        if symbols:
            subscription["symbols"] = symbols

        await self.send(subscription)

        # Track subscription
        sub_key = f"{channel}:{','.join(symbols) if symbols else 'all'}"
        self.subscriptions.append(sub_key)

        self.logger.info("Subscribed", channel=channel, symbols=symbols)

    async def unsubscribe(self, channel: str, symbols: Optional[List[str]] = None):
        """
        Unsubscribe from channel

        Args:
            channel: Channel name
            symbols: List of symbols to unsubscribe
        """
        unsubscription = {
            "action": "unsubscribe",
            "channel": channel
        }

        if symbols:
            unsubscription["symbols"] = symbols

        await self.send(unsubscription)

        # Remove from subscriptions
        sub_key = f"{channel}:{','.join(symbols) if symbols else 'all'}"
        if sub_key in self.subscriptions:
            self.subscriptions.remove(sub_key)

        self.logger.info("Unsubscribed", channel=channel, symbols=symbols)

    async def listen(self):
        """
        Listen for messages from WebSocket
        This should be run as a background task
        """
        while self.running:
            try:
                if not self.websocket or self.state != ConnectionState.CONNECTED:
                    await self._reconnect()
                    continue

                message = await self.websocket.recv()
                self.messages_received += 1
                self.last_message_time = datetime.utcnow()

                # Parse message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    self.errors_count += 1
                    self.logger.error(
                        "Invalid JSON received",
                        message=message[:100],  # Truncate long messages
                        error=str(e)
                    )
                    continue

                # Add to message queue
                await self.message_queue.put(data)

                # Handle message
                if self.on_message:
                    try:
                        await self.on_message(data)
                    except Exception as e:
                        self.errors_count += 1
                        self.logger.error("Error in message handler", error=str(e), exc_info=True)

            except websockets.exceptions.ConnectionClosed as e:
                self.state = ConnectionState.DISCONNECTED
                self.logger.warning(
                    "WebSocket connection closed",
                    code=e.code if hasattr(e, 'code') else None,
                    reason=e.reason if hasattr(e, 'reason') else None
                )
                await self._reconnect()

            except asyncio.CancelledError:
                self.logger.info("Listen task cancelled")
                break

            except Exception as e:
                self.errors_count += 1
                self.logger.error("Error in listen loop", error=str(e), exc_info=True)
                if self.on_error:
                    await self.on_error(e)

                await asyncio.sleep(1)

    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.state = ConnectionState.FAILED
            self.logger.error(
                "Max reconnection attempts reached",
                attempts=self.reconnect_attempts,
                max_attempts=self.max_reconnect_attempts
            )
            self.running = False
            return

        self.state = ConnectionState.RECONNECTING
        self.reconnect_attempts += 1

        # Exponential backoff: base_delay * (2 ^ attempts)
        wait_time = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            60  # Max 60 seconds
        )

        self.logger.info(
            "Attempting to reconnect",
            attempt=self.reconnect_attempts,
            max_attempts=self.max_reconnect_attempts,
            wait_time=wait_time,
            state=self.state.value
        )

        await asyncio.sleep(wait_time)

        if await self.connect():
            # Re-subscribe to previous subscriptions
            await self._resubscribe()
            self.logger.info(
                "Reconnection successful",
                attempt=self.reconnect_attempts,
                subscriptions=len(self.subscriptions)
            )

    async def _resubscribe(self):
        """Re-subscribe to previous subscriptions"""
        if not self.subscriptions:
            return

        self.logger.info("Re-subscribing to channels", count=len(self.subscriptions))

        # Store subscriptions to resubscribe
        subs_to_restore = self.subscriptions.copy()
        self.subscriptions.clear()

        for subscription in subs_to_restore:
            try:
                channel, symbols_str = subscription.split(":", 1)
                symbols = symbols_str.split(",") if symbols_str != "all" else None

                await self.subscribe(channel, symbols)
                await asyncio.sleep(0.1)  # Small delay between subscriptions

            except Exception as e:
                self.logger.error(
                    "Failed to re-subscribe",
                    subscription=subscription,
                    error=str(e)
                )

    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket statistics"""
        uptime = None
        if self.connection_time:
            uptime = (datetime.utcnow() - self.connection_time).total_seconds()

        return {
            "state": self.state.value,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "errors_count": self.errors_count,
            "reconnect_attempts": self.reconnect_attempts,
            "subscriptions": len(self.subscriptions),
            "uptime_seconds": uptime,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None
        }

    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.state == ConnectionState.CONNECTED and self.websocket is not None

    async def run(self):
        """
        Run WebSocket client
        Connects and starts listening
        """
        if await self.connect():
            await self.listen()


class MarketDataWebSocket:
    """
    Market data specific WebSocket client for Match-Trade Platform

    Features:
    - Real-time candle data streaming
    - Order book updates
    - Market watch (ticker) data
    - Trade updates
    - Automatic reconnection with exponential backoff
    - Connection state management
    """

    def __init__(self, token: str, trading_api_token: str):
        """
        Initialize Market Data WebSocket client

        Args:
            token: Authentication token
            trading_api_token: Trading API token
        """
        self.token = token
        self.trading_api_token = trading_api_token

        # Callbacks for different data types
        self.candle_callback: Optional[Callable] = None
        self.orderbook_callback: Optional[Callable] = None
        self.trade_callback: Optional[Callable] = None
        self.ticker_callback: Optional[Callable] = None
        self.market_watch_callback: Optional[Callable] = None

        # WebSocket client
        ws_url = settings.api_base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws/market-data"

        self.client = WebSocketClient(
            ws_url=ws_url,
            token=token,
            on_message=self._handle_message,
            on_error=self._handle_error,
            on_connect=self._handle_connect,
            on_disconnect=self._handle_disconnect
        )

        # Active subscriptions tracking
        self.active_candle_subscriptions: Dict[str, Dict[str, Any]] = {}
        self.active_orderbook_subscriptions: List[str] = []
        self.active_market_watch_subscriptions: List[str] = []

        self.logger = logger

    async def _handle_message(self, data: Dict[str, Any]):
        """Handle incoming message"""
        message_type = data.get("type") or data.get("event")

        try:
            if message_type == "candle" and self.candle_callback:
                await self.candle_callback(data.get("data"))

            elif message_type == "orderbook" and self.orderbook_callback:
                await self.orderbook_callback(data.get("data"))

            elif message_type == "trade" and self.trade_callback:
                await self.trade_callback(data.get("data"))

            elif message_type == "ticker" and self.ticker_callback:
                await self.ticker_callback(data.get("data"))

            elif message_type == "market_watch" and self.market_watch_callback:
                await self.market_watch_callback(data.get("data"))

            elif message_type == "subscribed":
                self.logger.info("Subscription confirmed", channel=data.get("channel"))

            elif message_type == "error":
                self.logger.error("WebSocket error message", error=data.get("message"))

            else:
                self.logger.debug("Unhandled message type", type=message_type, data=data)

        except Exception as e:
            self.logger.error("Error handling message", error=str(e), message_type=message_type)

    async def _handle_error(self, error: Exception):
        """Handle error"""
        self.logger.error("WebSocket error", error=str(error))

    async def _handle_connect(self):
        """Handle connection"""
        self.logger.info("Market data WebSocket connected")

    async def _handle_disconnect(self):
        """Handle disconnection"""
        self.logger.info("Market data WebSocket disconnected")

    async def subscribe_candles(
        self,
        symbols: List[str],
        timeframe: str = "1m",
        callback: Optional[Callable] = None
    ):
        """
        Subscribe to real-time candle updates

        Args:
            symbols: List of symbols to subscribe
            timeframe: Candle timeframe (1m, 5m, 15m, etc.)
            callback: Optional callback for candle data
        """
        if callback:
            self.candle_callback = callback

        for symbol in symbols:
            subscription_data = {
                "action": "subscribe",
                "channel": "candles",
                "symbol": symbol,
                "timeframe": timeframe
            }
            await self.client.send(subscription_data)
            self.active_candle_subscriptions[symbol] = {
                "timeframe": timeframe,
                "subscribed_at": datetime.utcnow()
            }

        self.logger.info(
            "Subscribed to candles",
            symbols=symbols,
            timeframe=timeframe,
            total_subscriptions=len(self.active_candle_subscriptions)
        )

    async def subscribe_orderbook(
        self,
        symbols: List[str],
        callback: Optional[Callable] = None
    ):
        """
        Subscribe to real-time order book updates

        Args:
            symbols: List of symbols to subscribe
            callback: Optional callback for orderbook data
        """
        if callback:
            self.orderbook_callback = callback

        await self.client.subscribe("orderbook", symbols)
        self.active_orderbook_subscriptions.extend(symbols)

        self.logger.info(
            "Subscribed to orderbook",
            symbols=symbols,
            total_subscriptions=len(self.active_orderbook_subscriptions)
        )

    async def subscribe_market_watch(
        self,
        symbols: List[str],
        callback: Optional[Callable] = None
    ):
        """
        Subscribe to real-time market watch (ticker) updates

        Args:
            symbols: List of symbols to subscribe
            callback: Optional callback for market watch data
        """
        if callback:
            self.market_watch_callback = callback

        await self.client.subscribe("market-watch", symbols)
        self.active_market_watch_subscriptions.extend(symbols)

        self.logger.info(
            "Subscribed to market watch",
            symbols=symbols,
            total_subscriptions=len(self.active_market_watch_subscriptions)
        )

    async def subscribe_trades(
        self,
        symbols: List[str],
        callback: Optional[Callable] = None
    ):
        """
        Subscribe to real-time trade updates

        Args:
            symbols: List of symbols to subscribe
            callback: Optional callback for trade data
        """
        if callback:
            self.trade_callback = callback

        await self.client.subscribe("trades", symbols)

        self.logger.info("Subscribed to trades", symbols=symbols)

    async def unsubscribe_candles(self, symbols: List[str]):
        """Unsubscribe from candle updates"""
        for symbol in symbols:
            await self.client.send({
                "action": "unsubscribe",
                "channel": "candles",
                "symbol": symbol
            })
            self.active_candle_subscriptions.pop(symbol, None)

        self.logger.info("Unsubscribed from candles", symbols=symbols)

    async def unsubscribe_orderbook(self, symbols: List[str]):
        """Unsubscribe from order book updates"""
        await self.client.unsubscribe("orderbook", symbols)
        for symbol in symbols:
            if symbol in self.active_orderbook_subscriptions:
                self.active_orderbook_subscriptions.remove(symbol)

        self.logger.info("Unsubscribed from orderbook", symbols=symbols)

    async def start(self):
        """Start WebSocket client"""
        self.logger.info("Starting Market Data WebSocket")
        await self.client.run()

    async def stop(self):
        """Stop WebSocket client"""
        self.logger.info("Stopping Market Data WebSocket")
        await self.client.disconnect()

    def get_statistics(self) -> Dict[str, Any]:
        """Get Market Data WebSocket statistics"""
        client_stats = self.client.get_statistics()

        return {
            **client_stats,
            "candle_subscriptions": len(self.active_candle_subscriptions),
            "orderbook_subscriptions": len(self.active_orderbook_subscriptions),
            "market_watch_subscriptions": len(self.active_market_watch_subscriptions),
            "candle_symbols": list(self.active_candle_subscriptions.keys()),
            "orderbook_symbols": self.active_orderbook_subscriptions,
            "market_watch_symbols": self.active_market_watch_subscriptions
        }

    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.client.is_connected()

    async def wait_for_connection(self, timeout: float = 10.0) -> bool:
        """
        Wait for WebSocket connection to be established

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if connected within timeout
        """
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            if self.is_connected():
                return True
            await asyncio.sleep(0.1)

        return False
