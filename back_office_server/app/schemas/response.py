"""
Generic response schemas
"""

from pydantic import BaseModel
from typing import Optional, Any, List


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None


class SessionInfo(BaseModel):
    """Session information"""
    session_id: int
    user_id: int
    trading_account_id: Optional[str] = None
    login_at: Optional[str] = None
    expires_at: Optional[str] = None
    last_refresh_at: Optional[str] = None


class SessionListResponse(BaseModel):
    """List of active sessions"""
    total: int
    sessions: List[SessionInfo]


class SessionHealthResponse(BaseModel):
    """Session health check response"""
    total_sessions: int
    healthy: int
    expiring_soon: int
    expired: int
    healthy_user_ids: List[int] = []
    expiring_user_ids: List[int] = []
    expired_user_ids: List[int] = []


class DashboardOverview(BaseModel):
    """Dashboard overview statistics"""
    total_users: int
    active_sessions: int
    total_balance: float
    total_equity: float
    total_profit_loss: float
    open_positions: int
    total_trades_today: int
    win_rate: float
    average_profit: float


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    period: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_loss: float
    average_profit: float
    average_loss: float
    best_trade: float
    worst_trade: float
    average_duration_seconds: int
