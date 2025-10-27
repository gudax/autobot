"""
Order model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.config.database import Base


class Order(Base):
    """Order model for storing order information"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    order_uuid = Column(String(100), unique=True, nullable=True)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # LONG/SHORT
    order_type = Column(String(20), nullable=True)  # MARKET/LIMIT
    quantity = Column(Numeric(18, 8), nullable=True)
    entry_price = Column(Numeric(18, 8), nullable=True)
    stop_loss = Column(Numeric(18, 8), nullable=True)
    take_profit = Column(Numeric(18, 8), nullable=True)
    status = Column(String(20), nullable=True, index=True)  # PENDING/OPEN/CLOSED/CANCELLED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    account = relationship("Account", back_populates="orders")
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, symbol='{self.symbol}', side='{self.side}', status='{self.status}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "order_uuid": self.order_uuid,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": float(self.quantity) if self.quantity else None,
            "entry_price": float(self.entry_price) if self.entry_price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }
