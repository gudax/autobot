"""
Signal Generator - Generates trading signals based on analysis
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logger import get_logger


logger = get_logger("signal_generator")


class SignalAction(str, Enum):
    """Trading signal action"""
    OPEN_LONG = "OPEN_LONG"
    OPEN_SHORT = "OPEN_SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """
    Complete trading signal with all parameters
    """
    action: SignalAction
    symbol: str
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 to 1.0
    reason: str
    timestamp: int

    # Optional metadata
    volume_signal_strength: float = 0.0
    orderbook_imbalance: float = 0.5
    rsi: float = 50.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "volume_signal_strength": self.volume_signal_strength,
            "orderbook_imbalance": self.orderbook_imbalance,
            "rsi": self.rsi
        }


class SignalGenerator:
    """
    Generates trading signals from analysis results
    """

    def __init__(self):
        self.logger = logger

    def generate_entry_signal(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        quantity: float,
        confidence: float,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TradingSignal:
        """
        Generate entry signal

        Args:
            symbol: Trading symbol
            direction: LONG or SHORT
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            quantity: Position quantity
            confidence: Signal confidence (0-1)
            reason: Signal reason
            metadata: Additional metadata

        Returns:
            TradingSignal
        """
        action = SignalAction.OPEN_LONG if direction == "LONG" else SignalAction.OPEN_SHORT

        signal = TradingSignal(
            action=action,
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reason=reason,
            timestamp=int(datetime.utcnow().timestamp())
        )

        if metadata:
            signal.volume_signal_strength = metadata.get("volume_signal_strength", 0.0)
            signal.orderbook_imbalance = metadata.get("orderbook_imbalance", 0.5)
            signal.rsi = metadata.get("rsi", 50.0)

        self.logger.info(
            "Entry signal generated",
            symbol=symbol,
            action=action.value,
            confidence=confidence,
            entry_price=entry_price
        )

        return signal

    def generate_exit_signal(
        self,
        symbol: str,
        exit_price: float,
        reason: str
    ) -> TradingSignal:
        """
        Generate exit signal

        Args:
            symbol: Trading symbol
            exit_price: Exit price
            reason: Exit reason

        Returns:
            TradingSignal
        """
        signal = TradingSignal(
            action=SignalAction.CLOSE,
            symbol=symbol,
            entry_price=exit_price,
            quantity=0.0,  # Will be determined by position manager
            stop_loss=0.0,
            take_profit=0.0,
            confidence=1.0,
            reason=reason,
            timestamp=int(datetime.utcnow().timestamp())
        )

        self.logger.info(
            "Exit signal generated",
            symbol=symbol,
            reason=reason,
            exit_price=exit_price
        )

        return signal

    def generate_hold_signal(self, symbol: str, reason: str = "No action needed") -> TradingSignal:
        """
        Generate hold signal

        Args:
            symbol: Trading symbol
            reason: Reason for holding

        Returns:
            TradingSignal
        """
        signal = TradingSignal(
            action=SignalAction.HOLD,
            symbol=symbol,
            entry_price=0.0,
            quantity=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            confidence=0.0,
            reason=reason,
            timestamp=int(datetime.utcnow().timestamp())
        )

        return signal
