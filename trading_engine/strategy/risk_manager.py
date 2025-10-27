"""
Risk Manager - Manages trading risks and position sizing
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from config.strategy_config import RiskManagementConfig
from utils.logger import get_logger
from utils.helpers import calculate_position_size


logger = get_logger("risk_manager")


@dataclass
class Position:
    """Open position"""
    symbol: str
    side: str  # LONG or SHORT
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L"""
        if self.current_price == 0:
            return 0.0

        if self.side == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        else:  # SHORT
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_percent(self) -> float:
        """Calculate unrealized P&L percentage"""
        if self.entry_price == 0:
            return 0.0

        if self.side == "LONG":
            return ((self.current_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - self.current_price) / self.entry_price) * 100

    @property
    def hold_duration(self) -> int:
        """Get position hold duration in seconds"""
        return int((datetime.utcnow() - self.entry_time).total_seconds())


@dataclass
class AccountState:
    """Account state for risk management"""
    balance: float
    equity: float
    open_positions: List[Position] = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0

    @property
    def position_count(self) -> int:
        """Get number of open positions"""
        return len(self.open_positions)

    @property
    def total_exposure(self) -> float:
        """Calculate total exposure"""
        return sum(pos.entry_price * pos.quantity for pos in self.open_positions)

    @property
    def total_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L"""
        return sum(pos.unrealized_pnl for pos in self.open_positions)


class RiskManager:
    """
    Manages trading risks including position sizing, drawdown limits, and risk checks
    """

    def __init__(
        self,
        config: Optional[RiskManagementConfig] = None,
        initial_balance: float = 10000.0
    ):
        """
        Initialize Risk Manager

        Args:
            config: Risk management configuration
            initial_balance: Initial account balance
        """
        self.config = config or RiskManagementConfig()
        self.initial_balance = initial_balance
        self.logger = logger

        # Account state
        self.account = AccountState(
            balance=initial_balance,
            equity=initial_balance
        )

        # Trading statistics
        self.daily_start_balance = initial_balance
        self.daily_reset_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        # Emergency stop flag
        self.emergency_stop_triggered = False

    def reset_daily_stats(self):
        """Reset daily statistics"""
        current_time = datetime.utcnow()
        reset_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        if current_time >= reset_time + timedelta(days=1):
            self.daily_start_balance = self.account.balance
            self.account.daily_pnl = 0.0
            self.daily_reset_time = reset_time
            self.logger.info("Daily statistics reset")

    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        risk_percent: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on risk

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_percent: Risk percentage (uses config if None)

        Returns:
            Position size
        """
        if risk_percent is None:
            risk_percent = self.config.max_risk_per_trade

        position_size = calculate_position_size(
            account_balance=self.account.balance,
            risk_percent=risk_percent,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            leverage=1  # Adjust as needed
        )

        self.logger.debug(
            "Position size calculated",
            symbol=symbol,
            position_size=position_size,
            risk_percent=risk_percent
        )

        return position_size

    def can_open_position(
        self,
        symbol: str,
        direction: str,
        position_size: float,
        entry_price: float
    ) -> Dict[str, Any]:
        """
        Check if a new position can be opened

        Args:
            symbol: Trading symbol
            direction: LONG or SHORT
            position_size: Proposed position size
            entry_price: Entry price

        Returns:
            Dictionary with check results
        """
        reasons = []
        can_open = True

        # Check emergency stop
        if self.emergency_stop_triggered:
            can_open = False
            reasons.append("Emergency stop triggered")

        # Check max positions
        positions_for_symbol = [p for p in self.account.open_positions if p.symbol == symbol]
        if len(positions_for_symbol) >= self.config.max_positions_per_symbol:
            can_open = False
            reasons.append(f"Max positions for {symbol} reached")

        if self.account.position_count >= self.config.max_total_positions:
            can_open = False
            reasons.append("Max total positions reached")

        # Check daily drawdown
        daily_drawdown = (self.daily_start_balance - self.account.balance) / self.daily_start_balance
        if daily_drawdown >= self.config.max_daily_drawdown:
            can_open = False
            reasons.append(f"Daily drawdown limit reached ({daily_drawdown:.2%})")

        # Check total drawdown
        total_drawdown = (self.initial_balance - self.account.balance) / self.initial_balance
        if total_drawdown >= self.config.max_total_drawdown:
            can_open = False
            reasons.append(f"Total drawdown limit reached ({total_drawdown:.2%})")

        # Check trading hours
        current_hour = datetime.utcnow().hour
        if not (self.config.trading_start_hour <= current_hour < self.config.trading_end_hour):
            can_open = False
            reasons.append("Outside trading hours")

        # Check available balance
        required_margin = position_size * entry_price
        if required_margin > self.account.balance * 0.9:  # Keep 10% buffer
            can_open = False
            reasons.append("Insufficient balance")

        return {
            "can_open": can_open,
            "reasons": reasons
        }

    def should_close_position(
        self,
        position: Position,
        current_price: float,
        max_hold_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if position should be closed

        Args:
            position: Position to check
            current_price: Current market price
            max_hold_time: Maximum hold time in seconds

        Returns:
            Dictionary with check results
        """
        should_close = False
        reasons = []

        # Update current price
        position.current_price = current_price

        # Check stop loss
        if position.side == "LONG":
            if current_price <= position.stop_loss:
                should_close = True
                reasons.append("Stop loss hit")
        else:  # SHORT
            if current_price >= position.stop_loss:
                should_close = True
                reasons.append("Stop loss hit")

        # Check take profit
        if position.side == "LONG":
            if current_price >= position.take_profit:
                should_close = True
                reasons.append("Take profit hit")
        else:  # SHORT
            if current_price <= position.take_profit:
                should_close = True
                reasons.append("Take profit hit")

        # Check max hold time
        if max_hold_time and position.hold_duration >= max_hold_time:
            should_close = True
            reasons.append(f"Max hold time exceeded ({position.hold_duration}s)")

        # Check emergency stop
        if self.emergency_stop_triggered:
            should_close = True
            reasons.append("Emergency stop triggered")

        return {
            "should_close": should_close,
            "reasons": reasons,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_percent": position.unrealized_pnl_percent
        }

    def add_position(self, position: Position):
        """
        Add opened position to tracking

        Args:
            position: Position to add
        """
        self.account.open_positions.append(position)
        self.logger.info(
            "Position added",
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price
        )

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Close position and update account

        Args:
            symbol: Trading symbol
            exit_price: Exit price
            reason: Closing reason

        Returns:
            Trade result dictionary or None
        """
        # Find position
        position = None
        for pos in self.account.open_positions:
            if pos.symbol == symbol:
                position = pos
                break

        if not position:
            self.logger.warning("Position not found", symbol=symbol)
            return None

        # Calculate P&L
        position.current_price = exit_price
        pnl = position.unrealized_pnl
        pnl_percent = position.unrealized_pnl_percent

        # Update account
        self.account.balance += pnl
        self.account.equity = self.account.balance
        self.account.daily_pnl += pnl
        self.account.total_pnl += pnl

        # Update statistics
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Remove position
        self.account.open_positions.remove(position)

        # Check emergency stop
        if self.config.emergency_stop_enabled:
            account_loss = (self.initial_balance - self.account.balance) / self.initial_balance
            if account_loss >= self.config.emergency_stop_loss_threshold:
                self.emergency_stop_triggered = True
                self.logger.error(
                    "EMERGENCY STOP TRIGGERED",
                    account_loss=account_loss,
                    threshold=self.config.emergency_stop_loss_threshold
                )

        trade_result = {
            "symbol": symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "quantity": position.quantity,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "duration": position.hold_duration,
            "reason": reason
        }

        self.logger.info(
            "Position closed",
            **trade_result
        )

        return trade_result

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get risk management statistics

        Returns:
            Dictionary with statistics
        """
        win_rate = (
            (self.winning_trades / self.total_trades * 100)
            if self.total_trades > 0 else 0
        )

        return {
            "balance": self.account.balance,
            "equity": self.account.equity,
            "initial_balance": self.initial_balance,
            "total_pnl": self.account.total_pnl,
            "daily_pnl": self.account.daily_pnl,
            "open_positions": self.account.position_count,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "emergency_stop": self.emergency_stop_triggered
        }

    def update_account_balance(self, new_balance: float):
        """Update account balance"""
        self.account.balance = new_balance
        self.account.equity = new_balance + self.account.total_unrealized_pnl
