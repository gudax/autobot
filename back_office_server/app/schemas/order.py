"""
Order and trading schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class TradingSignalRequest(BaseModel):
    """Schema for trading signal request"""
    action: str = Field(..., description="OPEN_LONG, OPEN_SHORT, CLOSE, or CLOSE_ALL")
    symbol: Optional[str] = Field(None, description="Trading symbol (e.g., BTCUSD)")
    entry_price: Optional[float] = Field(None, description="Entry price")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    volume: Optional[float] = Field(0.1, description="Order volume")
    strength: Optional[float] = Field(None, description="Signal strength (0-1)")
    volume_ratio: Optional[float] = Field(None, description="Volume ratio")
    orderbook_imbalance: Optional[float] = Field(None, description="Order book imbalance")
    reason: Optional[str] = Field(None, description="Signal reason/description")


class OrderResponse(BaseModel):
    """Schema for order response"""
    success: bool
    user_id: int
    order_id: Optional[int] = None
    order_uuid: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    volume: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    error: Optional[str] = None


class ExecuteSignalResponse(BaseModel):
    """Schema for signal execution response"""
    success: bool
    executed_count: int
    failed_count: int
    total_volume: Optional[float] = None
    execution_time_ms: Optional[float] = None
    successful_orders: List[OrderResponse] = []
    failed_orders: List[OrderResponse] = []
    signal: Optional[dict] = None
    error: Optional[str] = None


class ClosePositionsRequest(BaseModel):
    """Schema for closing positions"""
    symbol: Optional[str] = Field(None, description="Symbol to close (None = close all)")
    user_ids: Optional[List[int]] = Field(None, description="Specific user IDs (None = all users)")


class ClosePositionsResponse(BaseModel):
    """Schema for close positions response"""
    success: bool
    closed_count: int
    failed_count: int
    results: list


class OrderInfo(BaseModel):
    """Schema for order information"""
    id: int
    user_id: int
    symbol: str
    side: str
    order_type: Optional[str] = None
    quantity: Optional[Decimal] = None
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    status: str
    created_at: datetime
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TradeInfo(BaseModel):
    """Schema for trade information"""
    id: int
    user_id: int
    symbol: str
    side: str
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None
    profit_loss_percent: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    duration_seconds: Optional[int] = None
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Schema for position list response"""
    total: int
    positions: List[OrderInfo]
