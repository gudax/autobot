"""
WebSocket Manager

Manages WebSocket connections and broadcasts real-time updates
"""

import asyncio
import json
from typing import Dict, List, Set
from datetime import datetime
import logging
from fastapi import WebSocket, WebSocketState

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting

    Features:
    - Connection management (connect, disconnect)
    - Channel-based subscriptions
    - Broadcast messages to all or specific channels
    - Connection health monitoring
    """

    def __init__(self):
        """Initialize connection manager"""
        # All active connections
        self.active_connections: List[WebSocket] = []

        # Channel subscriptions: {channel_name: set of websockets}
        self.channels: Dict[str, Set[WebSocket]] = {
            "dashboard": set(),
            "trading": set(),
            "positions": set(),
            "sessions": set(),
            "all": set()
        }

        # Connection metadata: {websocket: metadata}
        self.connection_metadata: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, channel: str = "all"):
        """
        Accept a new WebSocket connection

        Args:
            websocket: WebSocket connection
            channel: Channel to subscribe to
        """
        await websocket.accept()

        self.active_connections.append(websocket)

        # Subscribe to channel
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(websocket)
        self.channels["all"].add(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "channel": channel,
            "connected_at": datetime.utcnow(),
            "messages_sent": 0
        }

        logger.info(f"WebSocket connected to channel '{channel}'. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection

        Args:
            websocket: WebSocket connection to remove
        """
        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from all channels
        for channel_connections in self.channels.values():
            channel_connections.discard(websocket)

        # Remove metadata
        channel = "unknown"
        if websocket in self.connection_metadata:
            channel = self.connection_metadata[websocket].get("channel", "unknown")
            del self.connection_metadata[websocket]

        logger.info(f"WebSocket disconnected from channel '{channel}'. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific connection

        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)

            # Update metadata
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]["messages_sent"] += 1

        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict, channel: str = "all"):
        """
        Broadcast a message to all connections in a channel with proper cleanup

        Args:
            message: Message to broadcast
            channel: Channel to broadcast to (default: "all")
        """
        if channel not in self.channels:
            logger.warning(f"Channel '{channel}' not found")
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        # Get connections for this channel (convert set to list for stable iteration)
        connections = list(self.channels[channel])

        if not connections:
            return

        # Check connection states before sending
        disconnected = []

        # Send messages with timeout protection
        send_tasks = []
        valid_connections = []

        for connection in connections:
            try:
                # Check WebSocket state before attempting send
                from fastapi import WebSocketState

                if not hasattr(connection, 'client_state'):
                    # Connection doesn't have state tracking, try to send anyway
                    valid_connections.append(connection)
                    send_tasks.append(self._send_with_timeout(connection, message))
                elif connection.client_state == WebSocketState.CONNECTED:
                    valid_connections.append(connection)
                    send_tasks.append(self._send_with_timeout(connection, message))
                else:
                    # Connection not in CONNECTED state
                    disconnected.append(connection)
                    logger.debug(f"Skipping disconnected WebSocket (state: {connection.client_state})")

            except Exception as e:
                logger.error(f"Error checking connection state: {e}")
                disconnected.append(connection)

        # Send messages concurrently with timeout
        if send_tasks:
            results = await asyncio.gather(*send_tasks, return_exceptions=True)

            # Process results
            for connection, result in zip(valid_connections, results):
                if isinstance(result, Exception):
                    logger.error(f"Error broadcasting to connection: {result}")
                    disconnected.append(connection)
                elif result:
                    # Update metadata on successful send
                    if connection in self.connection_metadata:
                        self.connection_metadata[connection]["messages_sent"] += 1

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

        successful_sends = len(valid_connections) - len(disconnected)
        logger.debug(f"Broadcasted message to {successful_sends}/{len(connections)} connections in channel '{channel}'")

    async def _send_with_timeout(self, connection: WebSocket, message: dict, timeout: float = 5.0):
        """
        Send message with timeout protection

        Args:
            connection: WebSocket connection
            message: Message to send
            timeout: Timeout in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            await asyncio.wait_for(
                connection.send_json(message),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Send timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Send failed: {e}")
            raise

    async def broadcast_position_update(self, position_data: dict):
        """
        Broadcast position update

        Args:
            position_data: Position information
        """
        message = {
            "type": "position_update",
            "data": position_data
        }
        await self.broadcast(message, "positions")
        await self.broadcast(message, "dashboard")

    async def broadcast_balance_update(self, balance_data: dict):
        """
        Broadcast balance update

        Args:
            balance_data: Balance information
        """
        message = {
            "type": "balance_update",
            "data": balance_data
        }
        await self.broadcast(message, "dashboard")

    async def broadcast_trade_signal(self, signal_data: dict):
        """
        Broadcast trading signal

        Args:
            signal_data: Signal information
        """
        message = {
            "type": "trade_signal",
            "data": signal_data
        }
        await self.broadcast(message, "trading")
        await self.broadcast(message, "dashboard")

    async def broadcast_order_executed(self, order_data: dict):
        """
        Broadcast order execution

        Args:
            order_data: Order information
        """
        message = {
            "type": "order_executed",
            "data": order_data
        }
        await self.broadcast(message, "trading")
        await self.broadcast(message, "positions")
        await self.broadcast(message, "dashboard")

    async def broadcast_position_closed(self, trade_data: dict):
        """
        Broadcast position closure

        Args:
            trade_data: Trade information
        """
        message = {
            "type": "position_closed",
            "data": trade_data
        }
        await self.broadcast(message, "positions")
        await self.broadcast(message, "dashboard")

    async def broadcast_session_update(self, session_data: dict):
        """
        Broadcast session update

        Args:
            session_data: Session information
        """
        message = {
            "type": "session_update",
            "data": session_data
        }
        await self.broadcast(message, "sessions")
        await self.broadcast(message, "dashboard")

    async def broadcast_error(self, error_message: str, channel: str = "all"):
        """
        Broadcast error message

        Args:
            error_message: Error message
            channel: Channel to broadcast to
        """
        message = {
            "type": "error",
            "error": error_message
        }
        await self.broadcast(message, channel)

    def get_statistics(self) -> dict:
        """
        Get connection statistics

        Returns:
            Statistics dictionary
        """
        channel_stats = {}
        for channel_name, connections in self.channels.items():
            channel_stats[channel_name] = len(connections)

        return {
            "total_connections": len(self.active_connections),
            "channels": channel_stats,
            "connections": [
                {
                    "channel": meta.get("channel"),
                    "connected_at": meta.get("connected_at").isoformat() if meta.get("connected_at") else None,
                    "messages_sent": meta.get("messages_sent", 0)
                }
                for meta in self.connection_metadata.values()
            ]
        }


# Global connection manager instance
ws_manager = ConnectionManager()
