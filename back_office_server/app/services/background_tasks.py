"""
Background Tasks

Handles scheduled background tasks:
- Session token refresh
- Session health monitoring
- Position monitoring
- Statistics updates
"""

import asyncio
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import AsyncSessionLocal
from app.config.settings import settings
from app.services.session_manager import SessionManager
from app.services.order_orchestrator import OrderOrchestrator
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages all background tasks

    Tasks:
    - Session token refresh (every 10 minutes)
    - Session health check (every 5 minutes)
    - Position monitoring (continuous)
    - WebSocket heartbeat (every 30 seconds)
    """

    def __init__(self):
        """Initialize background task manager"""
        self.running = False
        self.tasks = []

    async def start(self):
        """Start all background tasks"""
        if self.running:
            logger.warning("Background tasks already running")
            return

        self.running = True
        logger.info("Starting background tasks...")

        # Start all tasks
        self.tasks = [
            asyncio.create_task(self._session_refresh_task()),
            asyncio.create_task(self._session_health_task()),
            asyncio.create_task(self._position_monitoring_task()),
            asyncio.create_task(self._websocket_heartbeat_task()),
        ]

        logger.info(f"Started {len(self.tasks)} background tasks")

    async def stop(self):
        """Stop all background tasks"""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping background tasks...")

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        self.tasks = []
        logger.info("All background tasks stopped")

    async def _session_refresh_task(self):
        """
        Periodically refresh session tokens

        Runs every SESSION_REFRESH_INTERVAL_MINUTES
        """
        interval = settings.SESSION_REFRESH_INTERVAL_MINUTES * 60  # Convert to seconds

        logger.info(f"Session refresh task started (interval: {interval}s)")

        while self.running:
            try:
                await asyncio.sleep(interval)

                logger.info("Running session token refresh...")

                # Create database session
                async with AsyncSessionLocal() as db:
                    session_manager = SessionManager(db)

                    # Refresh all tokens
                    result = await session_manager.refresh_all_tokens()

                    logger.info(
                        f"Token refresh completed: {result['successful_refreshes']}/{result['total_sessions']} successful"
                    )

                    # Broadcast session update
                    await ws_manager.broadcast_session_update({
                        "type": "tokens_refreshed",
                        "successful": result['successful_refreshes'],
                        "failed": result['total_sessions'] - result['successful_refreshes']
                    })

                    await session_manager.close()

            except asyncio.CancelledError:
                logger.info("Session refresh task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session refresh task: {e}", exc_info=True)
                # Continue running even if there's an error
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _session_health_task(self):
        """
        Periodically check session health

        Runs every 5 minutes
        """
        interval = 300  # 5 minutes

        logger.info(f"Session health check task started (interval: {interval}s)")

        while self.running:
            try:
                await asyncio.sleep(interval)

                logger.info("Running session health check...")

                # Create database session
                async with AsyncSessionLocal() as db:
                    session_manager = SessionManager(db)

                    # Check session health
                    health_report = await session_manager.check_session_health()

                    logger.info(
                        f"Session health: {health_report['healthy']} healthy, "
                        f"{health_report['expiring_soon']} expiring soon, "
                        f"{health_report['expired']} expired"
                    )

                    # Broadcast health status
                    await ws_manager.broadcast_session_update({
                        "type": "session_health",
                        "healthy": health_report['healthy'],
                        "expiring_soon": health_report['expiring_soon'],
                        "expired": health_report['expired']
                    })

                    await session_manager.close()

            except asyncio.CancelledError:
                logger.info("Session health task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session health task: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _position_monitoring_task(self):
        """
        Continuously monitor open positions and auto-close based on conditions

        Checks positions every 5 seconds with fresh DB session
        """
        logger.info("Position monitoring task started")

        while self.running:
            try:
                # Create fresh database session for each check
                async with AsyncSessionLocal() as db:
                    orchestrator = OrderOrchestrator(db)

                    # Check positions once (new improved method)
                    result = await orchestrator.monitor_positions_once()

                    logger.debug(
                        f"Position check: {result['checked']} users checked, "
                        f"{result['closed']} positions closed, "
                        f"{result['errors']} errors"
                    )

                    # Get all open positions for broadcast
                    open_positions = await orchestrator.get_open_positions()

                    if open_positions:
                        # Broadcast position count update
                        await ws_manager.broadcast_position_update({
                            "type": "positions_count",
                            "count": len(open_positions),
                            "checked": result['checked'],
                            "closed": result['closed'],
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    await orchestrator.close()

                # Check positions every 5 seconds
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                logger.info("Position monitoring task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in position monitoring task: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _websocket_heartbeat_task(self):
        """
        Send heartbeat to all WebSocket connections

        Runs every 30 seconds
        """
        interval = 30  # 30 seconds

        logger.info(f"WebSocket heartbeat task started (interval: {interval}s)")

        while self.running:
            try:
                await asyncio.sleep(interval)

                # Send heartbeat to all connections
                await ws_manager.broadcast(
                    {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat(),
                        "connections": len(ws_manager.active_connections)
                    },
                    "all"
                )

            except asyncio.CancelledError:
                logger.info("WebSocket heartbeat task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat task: {e}", exc_info=True)
                await asyncio.sleep(interval)


# Global background task manager
background_tasks = BackgroundTaskManager()
