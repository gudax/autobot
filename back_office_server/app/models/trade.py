"""
Trade model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.config.database import Base


class Trade(Base):
    """Trade model for storing completed trade information"""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(50), nullable=True, index=True)
    side = Column(String(10), nullable=True)  # LONG/SHORT
    entry_price = Column(Numeric(18, 8), nullable=True)
    exit_price = Column(Numeric(18, 8), nullable=True)
    quantity = Column(Numeric(18, 8), nullable=True)
    profit_loss = Column(Numeric(18, 8), nullable=True)
    profit_loss_percent = Column(Numeric(10, 4), nullable=True)
    commission = Column(Numeric(18, 8), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="trades")
    user = relationship("User", back_populates="trades")

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol='{self.symbol}', profit_loss={self.profit_loss})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "side": self.side,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "quantity": float(self.quantity) if self.quantity else None,
            "profit_loss": float(self.profit_loss) if self.profit_loss else None,
            "profit_loss_percent": float(self.profit_loss_percent) if self.profit_loss_percent else None,
            "commission": float(self.commission) if self.commission else None,
            "duration_seconds": self.duration_seconds,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
