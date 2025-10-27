"""
Account model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.config.database import Base


class Account(Base):
    """Account model for storing trading account information"""

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trading_account_uuid = Column(String(100), unique=True, nullable=True)
    balance = Column(Numeric(18, 8), nullable=True)
    equity = Column(Numeric(18, 8), nullable=True)
    margin = Column(Numeric(18, 8), nullable=True)
    free_margin = Column(Numeric(18, 8), nullable=True)
    leverage = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    orders = relationship("Order", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account(id={self.id}, user_id={self.user_id}, balance={self.balance})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "trading_account_uuid": self.trading_account_uuid,
            "balance": float(self.balance) if self.balance else None,
            "equity": float(self.equity) if self.equity else None,
            "margin": float(self.margin) if self.margin else None,
            "free_margin": float(self.free_margin) if self.free_margin else None,
            "leverage": self.leverage,
            "currency": self.currency,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
