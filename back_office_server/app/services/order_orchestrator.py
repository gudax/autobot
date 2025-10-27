"""
Order Orchestrator

Executes trading signals across all active user accounts simultaneously
Monitors positions and manages order lifecycle
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.services.mt_api_client import MatchTradeAPIClient, MatchTradeAPIError
from app.services.session_manager import SessionManager
from app.models import User, UserSession, Account, Order, Trade, TradingSignal
from app.config.settings import settings

logger = logging.getLogger(__name__)


class OrderOrchestrator:
    """
    Orchestrates order execution across multiple user accounts

    Features:
    - Simultaneous order execution for all users
    - Position monitoring
    - Automatic position closing based on conditions
    - Order result tracking
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize Order Orchestrator

        Args:
            db: Database session
        """
        self.db = db
        self.api_client = MatchTradeAPIClient()
        self.session_manager = SessionManager(db)
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None

    async def execute_signal_for_all(
        self,
        signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a trading signal for all active users

        Args:
            signal: Trading signal data
                {
                    "action": "OPEN_LONG" | "OPEN_SHORT" | "CLOSE",
                    "symbol": "BTCUSD",
                    "entry_price": 50000,
                    "stop_loss": 49900,
                    "take_profit": 50150,
                    "volume": 0.1,
                    "reason": "Volume spike + OB imbalance"
                }

        Returns:
            Execution results
        """
        logger.info(f"Executing signal for all users: {signal['action']} {signal.get('symbol', '')}")

        # Save signal to database
        await self._save_signal(signal)

        # Get all active sessions
        active_sessions = await self.session_manager.get_active_sessions()

        if not active_sessions:
            logger.warning("No active sessions found, cannot execute signal")
            return {
                "success": False,
                "error": "No active sessions",
                "executed_count": 0,
                "failed_count": 0
            }

        # Determine action type
        action = signal.get("action", "").upper()

        if action in ["OPEN_LONG", "OPEN_SHORT"]:
            return await self._execute_open_orders(signal, active_sessions)
        elif action in ["CLOSE", "CLOSE_ALL"]:
            return await self._execute_close_orders(signal, active_sessions)
        else:
            logger.error(f"Unknown action: {action}")
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "executed_count": 0,
                "failed_count": 0
            }

    async def _execute_open_orders(
        self,
        signal: Dict[str, Any],
        sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute open orders for all active sessions

        Args:
            signal: Trading signal
            sessions: List of active sessions

        Returns:
            Execution results
        """
        symbol = signal.get("symbol")
        action = signal.get("action")
        side = "BUY" if action == "OPEN_LONG" else "SELL"
        volume = signal.get("volume", 0.1)
        stop_loss = signal.get("stop_loss")
        take_profit = signal.get("take_profit")

        logger.info(f"Opening {side} positions for {len(sessions)} users: {symbol}")

        # Execute orders concurrently
        tasks = [
            self._execute_order_for_user(
                session=session,
                symbol=symbol,
                side=side,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                signal_reason=signal.get("reason", "")
            )
            for session in sessions
        ]

        start_time = datetime.utcnow()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Process results
        successful_results = []
        failed_results = []
        total_volume = 0.0

        for result in results:
            if isinstance(result, dict):
                if result.get("success"):
                    successful_results.append(result)
                    total_volume += result.get("volume", 0.0)
                else:
                    failed_results.append(result)
            else:
                failed_results.append({
                    "success": False,
                    "error": str(result)
                })

        logger.info(
            f"Order execution completed: {len(successful_results)} successful, "
            f"{len(failed_results)} failed, execution time: {execution_time_ms:.2f}ms"
        )

        return {
            "success": True,
            "signal": {
                "action": action,
                "symbol": symbol,
                "side": side
            },
            "executed_count": len(successful_results),
            "failed_count": len(failed_results),
            "total_volume": total_volume,
            "execution_time_ms": execution_time_ms,
            "successful_orders": successful_results,
            "failed_orders": failed_results
        }

    async def _execute_order_for_user(
        self,
        session: Dict[str, Any],
        symbol: str,
        side: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_reason: str = ""
    ) -> Dict[str, Any]:
        """
        Execute an order for a specific user

        Args:
            session: User session data
            symbol: Trading symbol
            side: BUY or SELL
            volume: Order volume
            stop_loss: Stop loss price
            take_profit: Take profit price
            signal_reason: Reason for the signal

        Returns:
            Order execution result
        """
        user_id = session["user_id"]
        token = session["token"]
        trading_api_token = session["trading_api_token"]

        try:
            # Get user's account info for position sizing
            balance_info = await self.api_client.get_balance(token, trading_api_token)

            # Adjust volume based on account balance (optional risk management)
            adjusted_volume = self._calculate_position_size(balance_info, volume)

            # Execute order via API
            position = await self.api_client.open_position(
                token=token,
                trading_api_token=trading_api_token,
                symbol=symbol,
                side=side,
                volume=adjusted_volume,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            # Save order to database
            order = Order(
                user_id=user_id,
                account_id=None,  # Will be updated when we sync account
                order_uuid=position.get("id") or position.get("uuid") or position.get("positionId"),
                symbol=symbol,
                side="LONG" if side == "BUY" else "SHORT",
                order_type="MARKET",
                quantity=Decimal(str(adjusted_volume)),
                entry_price=Decimal(str(position.get("entry_price") or position.get("openPrice", 0))),
                stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
                take_profit=Decimal(str(take_profit)) if take_profit else None,
                status="OPEN",
                executed_at=datetime.utcnow()
            )
            self.db.add(order)

            try:
                await self.db.commit()
                await self.db.refresh(order)
            except Exception as commit_error:
                await self.db.rollback()
                logger.error(f"Failed to commit order for user {user_id}: {commit_error}")
                raise

            logger.info(f"Order executed successfully for user {user_id}: {symbol} {side} {adjusted_volume}")

            return {
                "success": True,
                "user_id": user_id,
                "order_id": order.id,
                "order_uuid": order.order_uuid,
                "symbol": symbol,
                "side": side,
                "volume": adjusted_volume,
                "entry_price": float(position.get("entry_price") or position.get("openPrice", 0)),
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }

        except MatchTradeAPIError as e:
            logger.error(f"Order execution failed for user {user_id}: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error executing order for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def _execute_close_orders(
        self,
        signal: Dict[str, Any],
        sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Close positions for all active sessions

        Args:
            signal: Trading signal with close instructions
            sessions: List of active sessions

        Returns:
            Close results
        """
        symbol = signal.get("symbol")

        logger.info(f"Closing positions for {len(sessions)} users: {symbol or 'ALL'}")

        # Close orders concurrently
        tasks = [
            self._close_positions_for_user(
                session=session,
                symbol=symbol
            )
            for session in sessions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_closes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed_closes = len(results) - successful_closes

        logger.info(f"Close completed: {successful_closes} successful, {failed_closes} failed")

        return {
            "success": True,
            "closed_count": successful_closes,
            "failed_count": failed_closes,
            "results": [r if isinstance(r, dict) else {"success": False, "error": str(r)} for r in results]
        }

    async def _close_positions_for_user(
        self,
        session: Dict[str, Any],
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Close positions for a specific user

        Args:
            session: User session data
            symbol: Symbol to close (None = close all)

        Returns:
            Close result
        """
        user_id = session["user_id"]
        token = session["token"]
        trading_api_token = session["trading_api_token"]

        try:
            # Get open positions
            positions = await self.api_client.get_opened_positions(token, trading_api_token)

            # Filter by symbol if specified
            if symbol:
                positions = [p for p in positions if p.get("symbol") == symbol]

            if not positions:
                return {
                    "success": True,
                    "user_id": user_id,
                    "closed_count": 0,
                    "message": "No open positions to close"
                }

            # Close all positions
            close_tasks = [
                self.api_client.close_position(token, trading_api_token, p.get("id") or p.get("uuid"))
                for p in positions
            ]
            close_results = await asyncio.gather(*close_tasks, return_exceptions=True)

            # Update orders in database
            for position, result in zip(positions, close_results):
                if isinstance(result, dict) and not isinstance(result, Exception):
                    await self._record_trade(user_id, position, result)

            successful_closes = sum(1 for r in close_results if isinstance(r, dict))

            logger.info(f"Closed {successful_closes} positions for user {user_id}")

            return {
                "success": True,
                "user_id": user_id,
                "closed_count": successful_closes
            }

        except Exception as e:
            logger.error(f"Failed to close positions for user {user_id}: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def _record_trade(
        self,
        user_id: int,
        position: Dict[str, Any],
        close_result: Dict[str, Any]
    ):
        """
        Record a completed trade in the database

        Args:
            user_id: User ID
            position: Position data
            close_result: Close result data
        """
        try:
            # Find corresponding order - try multiple ID fields and fallback to symbol matching
            position_id = position.get("id") or position.get("uuid") or position.get("positionId")
            symbol = position.get("symbol")

            # First, try to find by exact UUID match
            result = await self.db.execute(
                select(Order).where(
                    Order.order_uuid == position_id,
                    Order.user_id == user_id
                )
            )
            order = result.scalar_one_or_none()

            # If not found by UUID, try to find most recent OPEN order for this symbol
            if not order and symbol:
                logger.info(f"Order not found by UUID {position_id}, trying symbol match for {symbol}")
                result = await self.db.execute(
                    select(Order).where(
                        Order.symbol == symbol,
                        Order.user_id == user_id,
                        Order.status == "OPEN"
                    ).order_by(Order.created_at.desc())
                )
                order = result.first()

            if not order:
                logger.warning(f"Order not found for position {position_id} / symbol {symbol}")
                return

            # Update order status
            order.status = "CLOSED"
            order.closed_at = datetime.utcnow()

            # Update order_uuid if it was matched by symbol (for future reference)
            if position_id and not order.order_uuid:
                order.order_uuid = position_id

            # Calculate trade metrics
            entry_price = float(position.get("entry_price") or position.get("openPrice", 0))
            exit_price = float(position.get("close_price") or close_result.get("closePrice", 0))
            volume = float(position.get("volume", 0))
            profit_loss = float(close_result.get("profit") or close_result.get("profitLoss", 0))

            # Calculate duration
            duration_seconds = None
            if order.executed_at:
                duration_seconds = int((datetime.utcnow() - order.executed_at).total_seconds())

            # Create trade record
            trade = Trade(
                order_id=order.id,
                user_id=user_id,
                symbol=order.symbol,
                side=order.side,
                entry_price=Decimal(str(entry_price)),
                exit_price=Decimal(str(exit_price)),
                quantity=Decimal(str(volume)),
                profit_loss=Decimal(str(profit_loss)),
                profit_loss_percent=Decimal(str((profit_loss / (entry_price * volume)) * 100)) if entry_price and volume else None,
                commission=Decimal(str(close_result.get("commission", 0))),
                duration_seconds=duration_seconds,
                executed_at=order.executed_at,
                closed_at=datetime.utcnow()
            )

            self.db.add(trade)

            try:
                await self.db.commit()
                logger.info(f"Trade recorded: {order.symbol} P&L: {profit_loss}")
            except Exception as commit_error:
                await self.db.rollback()
                logger.error(f"Failed to commit trade: {commit_error}")
                raise

        except Exception as e:
            logger.error(f"Failed to record trade: {e}", exc_info=True)

    async def monitor_positions_once(self):
        """
        Check all open positions once and close based on conditions
        This should be called periodically by background task manager

        Returns:
            Dictionary with monitoring results
        """
        try:
            logger.debug("Checking positions for all users...")

            # Get all active sessions
            active_sessions = await self.session_manager.get_active_sessions()

            if not active_sessions:
                return {
                    "checked": 0,
                    "closed": 0,
                    "errors": 0
                }

            # Check positions for all users
            closed_count = 0
            error_count = 0

            for session in active_sessions:
                try:
                    result = await self._check_user_positions(session)
                    if result and result.get('closed', 0) > 0:
                        closed_count += result['closed']
                except Exception as e:
                    logger.error(f"Error checking positions for user {session['user_id']}: {e}")
                    error_count += 1

            return {
                "checked": len(active_sessions),
                "closed": closed_count,
                "errors": error_count
            }

        except Exception as e:
            logger.error(f"Error in position monitoring: {e}", exc_info=True)
            return {
                "checked": 0,
                "closed": 0,
                "errors": 1
            }

    async def monitor_positions(self):
        """
        DEPRECATED: Use monitor_positions_once() called by background task manager instead

        Legacy continuous monitoring method - kept for backwards compatibility
        """
        logger.warning("monitor_positions() is deprecated. Use monitor_positions_once() in background tasks instead")
        self.monitoring_active = True
        logger.info("Starting legacy position monitoring...")

        while self.monitoring_active:
            try:
                await self.monitor_positions_once()
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in position monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _check_user_positions(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check positions for a specific user

        Args:
            session: User session data

        Returns:
            Dictionary with check results
        """
        user_id = session["user_id"]
        token = session["token"]
        trading_api_token = session["trading_api_token"]

        closed_count = 0

        try:
            # Get open positions from API
            positions = await self.api_client.get_opened_positions(token, trading_api_token)

            if not positions:
                return {"closed": 0, "positions": 0}

            for position in positions:
                # Check if position should be closed based on:
                # 1. Max holding time exceeded
                # 2. Target profit/loss reached
                # 3. Opposite signal received

                position_id = position.get("id") or position.get("uuid") or position.get("positionId")
                symbol = position.get("symbol")

                # Get order from database
                result = await self.db.execute(
                    select(Order).where(Order.order_uuid == position_id)
                )
                order = result.scalar_one_or_none()

                # If not found by UUID, try symbol match
                if not order and symbol:
                    result = await self.db.execute(
                        select(Order).where(
                            Order.symbol == symbol,
                            Order.user_id == user_id,
                            Order.status == "OPEN"
                        ).order_by(Order.created_at.desc())
                    )
                    order = result.first()

                if not order:
                    continue

                should_close = False
                close_reason = ""

                # Check max holding time (e.g., 5 minutes)
                if order.executed_at:
                    holding_time = (datetime.utcnow() - order.executed_at).total_seconds()
                    if holding_time > 300:  # 5 minutes
                        should_close = True
                        close_reason = "Max holding time exceeded"

                # Check profit/loss thresholds
                current_pl = float(position.get("profit") or position.get("profitLoss", 0))
                if current_pl >= 100:  # Example: close if profit >= $100
                    should_close = True
                    close_reason = "Target profit reached"
                elif current_pl <= -50:  # Example: close if loss >= $50
                    should_close = True
                    close_reason = "Stop loss triggered"

                if should_close:
                    logger.info(f"Auto-closing position {position_id} for user {user_id}: {close_reason}")
                    try:
                        close_result = await self.api_client.close_position(token, trading_api_token, position_id)
                        await self._record_trade(user_id, position, close_result)
                        closed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to auto-close position {position_id}: {e}")

            return {"closed": closed_count, "positions": len(positions)}

        except Exception as e:
            logger.error(f"Error checking positions for user {user_id}: {e}")
            return {"closed": closed_count, "positions": 0, "error": str(e)}

    def start_monitoring(self):
        """Start the position monitoring task"""
        if not self.monitoring_task or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self.monitor_positions())
            logger.info("Position monitoring started")

    def stop_monitoring(self):
        """Stop the position monitoring task"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            logger.info("Position monitoring stopped")

    async def _save_signal(self, signal: Dict[str, Any]):
        """
        Save trading signal to database

        Args:
            signal: Trading signal data
        """
        try:
            trading_signal = TradingSignal(
                symbol=signal.get("symbol"),
                signal_type=signal.get("action", "").replace("OPEN_", ""),
                strength=Decimal(str(signal.get("strength", 0))),
                volume_ratio=Decimal(str(signal.get("volume_ratio", 0))),
                orderbook_imbalance=Decimal(str(signal.get("orderbook_imbalance", 0))),
                price=Decimal(str(signal.get("entry_price", 0))),
                reason=signal.get("reason", "")
            )
            self.db.add(trading_signal)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")

    def _calculate_position_size(
        self,
        balance_info: Dict[str, Any],
        default_volume: float
    ) -> float:
        """
        Calculate position size based on account balance

        Args:
            balance_info: Account balance information
            default_volume: Default volume

        Returns:
            Adjusted volume
        """
        # Simple position sizing - can be enhanced with more sophisticated risk management
        balance = float(balance_info.get("balance", 0))

        if balance < 1000:
            return min(default_volume, 0.01)
        elif balance < 5000:
            return min(default_volume, 0.05)
        else:
            return default_volume

    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions across all users

        Returns:
            List of open positions with user info
        """
        result = await self.db.execute(
            select(Order)
            .where(Order.status == "OPEN")
            .join(User)
        )
        orders = result.scalars().all()

        return [order.to_dict() for order in orders]

    async def close(self):
        """Close resources"""
        self.stop_monitoring()
        await self.api_client.close()
        await self.session_manager.close()
