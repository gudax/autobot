"""
System log model
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.config.database import Base


class SystemLog(Base):
    """System log model for storing system events"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_level = Column(String(20), nullable=True, index=True)  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    component = Column(String(100), nullable=True, index=True)
    message = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<SystemLog(id={self.id}, log_level='{self.log_level}', component='{self.component}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            "id": self.id,
            "log_level": self.log_level,
            "component": self.component,
            "message": self.message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
