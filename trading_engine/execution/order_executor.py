"""
Order Executor - Executes orders on Match-Trade platform
"""

import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import aiohttp

from config import settings
from strategy.signal_generator import TradingSignal, SignalAction
from utils.logger import get_logger


logger = get_logger("order_executor")


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class OrderType(str, Enum):
    """Order type"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    filled_quantity: float = 0.0
    error_message: str = ""
    execution_time: float = 0.0
    timestamp: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "order_id": self.order_id,
            "status": self.status.value,
            "filled_price": self.filled_price,
            "filled_quantity": self.filled_quantity,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp
        }


class OrderExecutor:
    """
    Executes trading orders on Match-Trade platform
    Handles order submission, validation, retry logic, and status tracking
    """

    def __init__(
        self,
        token: str,
        trading_api_token: str,
        simulation_mode: bool = True
    ):
        """
        Initialize Order Executor

        Args:
            token: Authentication token
            trading_api_token: Trading API token
            simulation_mode: If True, simulates order execution without real trades
        """
        self.token = token
        self.trading_api_token = trading_api_token
        self.simulation_mode = simulation_mode
        self.base_url = settings.api_base_url
        self.timeout = aiohttp.ClientTimeout(total=settings.api_timeout)
        self.logger = logger

        # Session
        self._session: Optional[aiohttp.ClientSession] = None

        # Order tracking
        self.pending_orders: Dict[str, Dict[str, Any]] = {}
        self.filled_orders: List[Dict[str, Any]] = []

        self.logger.info(
            "Order Executor initialized",
            simulation_mode=simulation_mode
        )

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
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.token}",
            "TradingApiToken": self.trading_api_token
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Match-Trade API

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data

        Returns:
            API response data
        """
        await self._ensure_session()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with self._session.request(
                method=method,
                url=url,
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

        except Exception as e:
            self.logger.error("Request error", error=str(e), endpoint=endpoint)
            raise

    def validate_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """
        Validate trading signal before execution

        Args:
            signal: Trading signal to validate

        Returns:
            Dictionary with validation results
        """
        is_valid = True
        errors = []

        # Check action
        if signal.action == SignalAction.HOLD:
            is_valid = False
            errors.append("Cannot execute HOLD signal")

        # Check prices
        if signal.entry_price <= 0:
            is_valid = False
            errors.append("Invalid entry price")

        if signal.action in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]:
            if signal.stop_loss <= 0:
                is_valid = False
                errors.append("Invalid stop loss price")

            if signal.take_profit <= 0:
                is_valid = False
                errors.append("Invalid take profit price")

            if signal.quantity <= 0:
                is_valid = False
                errors.append("Invalid quantity")

            # Check stop loss vs entry price
            if signal.action == SignalAction.OPEN_LONG:
                if signal.stop_loss >= signal.entry_price:
                    is_valid = False
                    errors.append("Stop loss must be below entry for LONG")

                if signal.take_profit <= signal.entry_price:
                    is_valid = False
                    errors.append("Take profit must be above entry for LONG")

            elif signal.action == SignalAction.OPEN_SHORT:
                if signal.stop_loss <= signal.entry_price:
                    is_valid = False
                    errors.append("Stop loss must be above entry for SHORT")

                if signal.take_profit >= signal.entry_price:
                    is_valid = False
                    errors.append("Take profit must be below entry for SHORT")

        return {
            "is_valid": is_valid,
            "errors": errors
        }

    async def execute_signal(
        self,
        signal: TradingSignal,
        retry_attempts: int = 3
    ) -> OrderResult:
        """
        Execute trading signal

        Args:
            signal: Trading signal to execute
            retry_attempts: Number of retry attempts on failure

        Returns:
            OrderResult
        """
        start_time = datetime.utcnow()

        # Validate signal
        validation = self.validate_signal(signal)
        if not validation["is_valid"]:
            error_msg = " | ".join(validation["errors"])
            self.logger.error("Signal validation failed", errors=validation["errors"])
            return OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                error_message=error_msg,
                timestamp=int(start_time.timestamp())
            )

        # Execute based on action
        if signal.action in [SignalAction.OPEN_LONG, SignalAction.OPEN_SHORT]:
            result = await self._execute_open_position(signal, retry_attempts)
        elif signal.action == SignalAction.CLOSE:
            result = await self._execute_close_position(signal, retry_attempts)
        else:
            result = OrderResult(
                success=False,
                status=OrderStatus.REJECTED,
                error_message=f"Unsupported action: {signal.action}",
                timestamp=int(start_time.timestamp())
            )

        # Calculate execution time
        end_time = datetime.utcnow()
        result.execution_time = (end_time - start_time).total_seconds()

        return result

    async def _execute_open_position(
        self,
        signal: TradingSignal,
        retry_attempts: int
    ) -> OrderResult:
        """Execute open position order"""
        if self.simulation_mode:
            return self._simulate_open_position(signal)

        side = "LONG" if signal.action == SignalAction.OPEN_LONG else "SHORT"

        order_params = {
            "symbol": signal.symbol,
            "side": side,
            "type": "MARKET",
            "quantity": signal.quantity,
            "stopLoss": signal.stop_loss,
            "takeProfit": signal.take_profit
        }

        for attempt in range(retry_attempts):
            try:
                self.logger.info(
                    "Executing open position",
                    symbol=signal.symbol,
                    side=side,
                    quantity=signal.quantity,
                    attempt=attempt + 1
                )

                response = await self._make_request(
                    method="POST",
                    endpoint="/api/v1/positions/open",
                    data=order_params
                )

                order_id = response.get("data", {}).get("orderId")
                filled_price = response.get("data", {}).get("price", signal.entry_price)

                self.logger.info(
                    "Position opened successfully",
                    order_id=order_id,
                    filled_price=filled_price
                )

                return OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.FILLED,
                    filled_price=filled_price,
                    filled_quantity=signal.quantity,
                    timestamp=int(datetime.utcnow().timestamp())
                )

            except Exception as e:
                self.logger.error(
                    "Failed to open position",
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt == retry_attempts - 1:
                    return OrderResult(
                        success=False,
                        status=OrderStatus.FAILED,
                        error_message=str(e),
                        timestamp=int(datetime.utcnow().timestamp())
                    )

                # Wait before retry
                await asyncio.sleep(settings.api_retry_delay)

        return OrderResult(
            success=False,
            status=OrderStatus.FAILED,
            error_message="Max retry attempts reached",
            timestamp=int(datetime.utcnow().timestamp())
        )

    async def _execute_close_position(
        self,
        signal: TradingSignal,
        retry_attempts: int
    ) -> OrderResult:
        """Execute close position order"""
        if self.simulation_mode:
            return self._simulate_close_position(signal)

        for attempt in range(retry_attempts):
            try:
                self.logger.info(
                    "Executing close position",
                    symbol=signal.symbol,
                    attempt=attempt + 1
                )

                response = await self._make_request(
                    method="POST",
                    endpoint="/api/v1/positions/close",
                    data={"symbol": signal.symbol}
                )

                order_id = response.get("data", {}).get("orderId")
                filled_price = response.get("data", {}).get("price", signal.entry_price)

                self.logger.info(
                    "Position closed successfully",
                    order_id=order_id,
                    filled_price=filled_price
                )

                return OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.FILLED,
                    filled_price=filled_price,
                    timestamp=int(datetime.utcnow().timestamp())
                )

            except Exception as e:
                self.logger.error(
                    "Failed to close position",
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt == retry_attempts - 1:
                    return OrderResult(
                        success=False,
                        status=OrderStatus.FAILED,
                        error_message=str(e),
                        timestamp=int(datetime.utcnow().timestamp())
                    )

                await asyncio.sleep(settings.api_retry_delay)

        return OrderResult(
            success=False,
            status=OrderStatus.FAILED,
            error_message="Max retry attempts reached",
            timestamp=int(datetime.utcnow().timestamp())
        )

    def _simulate_open_position(self, signal: TradingSignal) -> OrderResult:
        """Simulate open position (for testing)"""
        import uuid

        order_id = f"sim_{uuid.uuid4().hex[:8]}"

        self.logger.info(
            "SIMULATION: Position opened",
            order_id=order_id,
            symbol=signal.symbol,
            side="LONG" if signal.action == SignalAction.OPEN_LONG else "SHORT",
            quantity=signal.quantity,
            entry_price=signal.entry_price
        )

        return OrderResult(
            success=True,
            order_id=order_id,
            status=OrderStatus.FILLED,
            filled_price=signal.entry_price,
            filled_quantity=signal.quantity,
            timestamp=int(datetime.utcnow().timestamp())
        )

    def _simulate_close_position(self, signal: TradingSignal) -> OrderResult:
        """Simulate close position (for testing)"""
        import uuid

        order_id = f"sim_{uuid.uuid4().hex[:8]}"

        self.logger.info(
            "SIMULATION: Position closed",
            order_id=order_id,
            symbol=signal.symbol,
            exit_price=signal.entry_price
        )

        return OrderResult(
            success=True,
            order_id=order_id,
            status=OrderStatus.FILLED,
            filled_price=signal.entry_price,
            timestamp=int(datetime.utcnow().timestamp())
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "pending_orders": len(self.pending_orders),
            "filled_orders": len(self.filled_orders),
            "simulation_mode": self.simulation_mode
        }
