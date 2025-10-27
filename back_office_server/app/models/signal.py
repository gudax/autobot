"""
Trading signal model
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text
from sqlalchemy.sql import func

from app.config.database import Base


class TradingSignal(Base):
    """Trading signal model for storing signal logs"""

    __tablename__ = "trading_signals"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=True, index=True)
    signal_type = Column(String(10), nullable=True, index=True)  # LONG/SHORT/CLOSE
    strength = Column(Numeric(5, 4), nullable=True)
    volume_ratio = Column(Numeric(10, 4), nullable=True)
    orderbook_imbalance = Column(Numeric(5, 4), nullable=True)
    price = Column(Numeric(18, 8), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<TradingSignal(id={self.id}, symbol='{self.symbol}', signal_type='{self.signal_type}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "strength": float(self.strength) if self.strength else None,
            "volume_ratio": float(self.volume_ratio) if self.volume_ratio else None,
            "orderbook_imbalance": float(self.orderbook_imbalance) if self.orderbook_imbalance else None,
            "price": float(self.price) if self.price else None,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
