"""
Dashboard API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.config.database import get_db
from app.models import User, UserSession, Order, Trade, Account
from app.schemas import DashboardOverview, PerformanceMetrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard overview statistics

    Returns:
    - Total users
    - Active sessions
    - Total balance and equity
    - Open positions
    - Today's trades count
    - Win rate
    - Average profit
    """
    try:
        # Total users
        total_users_result = await db.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar() or 0

        # Active sessions
        active_sessions_result = await db.execute(
            select(func.count(UserSession.id)).where(UserSession.is_active == True)
        )
        active_sessions = active_sessions_result.scalar() or 0

        # Total balance and equity
        accounts_result = await db.execute(
            select(
                func.sum(Account.balance),
                func.sum(Account.equity)
            )
        )
        balance_row = accounts_result.first()
        total_balance = float(balance_row[0] or 0)
        total_equity = float(balance_row[1] or 0)

        # Open positions
        open_positions_result = await db.execute(
            select(func.count(Order.id)).where(Order.status == "OPEN")
        )
        open_positions = open_positions_result.scalar() or 0

        # Today's trades
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_trades_result = await db.execute(
            select(func.count(Trade.id)).where(Trade.closed_at >= today_start)
        )
        total_trades_today = today_trades_result.scalar() or 0

        # Total P&L and win rate (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        trades_result = await db.execute(
            select(Trade).where(Trade.closed_at >= thirty_days_ago)
        )
        trades = trades_result.scalars().all()

        total_profit_loss = sum(float(t.profit_loss or 0) for t in trades)
        winning_trades = sum(1 for t in trades if (t.profit_loss or 0) > 0)
        win_rate = (winning_trades / len(trades) * 100) if trades else 0.0

        # Average profit (winning trades only)
        winning_profits = [float(t.profit_loss) for t in trades if (t.profit_loss or 0) > 0]
        average_profit = sum(winning_profits) / len(winning_profits) if winning_profits else 0.0

        return DashboardOverview(
            total_users=total_users,
            active_sessions=active_sessions,
            total_balance=total_balance,
            total_equity=total_equity,
            total_profit_loss=total_profit_loss,
            open_positions=open_positions,
            total_trades_today=total_trades_today,
            win_rate=round(win_rate, 2),
            average_profit=round(average_profit, 2)
        )

    except Exception as e:
        logger.error(f"Failed to get dashboard overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard overview: {str(e)}"
        )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period: str = "30d",
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics

    - **period**: Time period (7d, 30d, 90d, 1y)

    Returns detailed performance statistics
    """
    try:
        # Parse period
        period_days = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "1y": 365
        }.get(period, 30)

        start_date = datetime.utcnow() - timedelta(days=period_days)

        # Get trades in period
        result = await db.execute(
            select(Trade).where(Trade.closed_at >= start_date)
        )
        trades = result.scalars().all()

        if not trades:
            return PerformanceMetrics(
                period=period,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_profit_loss=0.0,
                average_profit=0.0,
                average_loss=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                average_duration_seconds=0
            )

        # Calculate metrics
        total_trades = len(trades)
        winning_trades_list = [t for t in trades if (t.profit_loss or 0) > 0]
        losing_trades_list = [t for t in trades if (t.profit_loss or 0) < 0]

        winning_trades = len(winning_trades_list)
        losing_trades = len(losing_trades_list)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        total_profit_loss = sum(float(t.profit_loss or 0) for t in trades)

        winning_profits = [float(t.profit_loss) for t in winning_trades_list]
        losing_profits = [float(t.profit_loss) for t in losing_trades_list]

        average_profit = sum(winning_profits) / len(winning_profits) if winning_profits else 0.0
        average_loss = sum(losing_profits) / len(losing_profits) if losing_profits else 0.0

        best_trade = max(winning_profits) if winning_profits else 0.0
        worst_trade = min(losing_profits) if losing_profits else 0.0

        # Average duration
        durations = [t.duration_seconds for t in trades if t.duration_seconds]
        average_duration = sum(durations) // len(durations) if durations else 0

        return PerformanceMetrics(
            period=period,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            total_profit_loss=round(total_profit_loss, 2),
            average_profit=round(average_profit, 2),
            average_loss=round(average_loss, 2),
            best_trade=round(best_trade, 2),
            worst_trade=round(worst_trade, 2),
            average_duration_seconds=average_duration
        )

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/users")
async def get_users_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard data for all users

    Returns individual performance for each user
    """
    try:
        # Get all users with their sessions and recent trades
        result = await db.execute(
            select(User)
        )
        users = result.scalars().all()

        user_data = []

        for user in users:
            # Get user's active session
            session_result = await db.execute(
                select(UserSession).where(
                    UserSession.user_id == user.id,
                    UserSession.is_active == True
                )
            )
            session = session_result.scalar_one_or_none()

            # Get user's trades (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            trades_result = await db.execute(
                select(Trade).where(
                    Trade.user_id == user.id,
                    Trade.closed_at >= thirty_days_ago
                )
            )
            trades = trades_result.scalars().all()

            total_pl = sum(float(t.profit_loss or 0) for t in trades)
            winning_trades = sum(1 for t in trades if (t.profit_loss or 0) > 0)
            win_rate = (winning_trades / len(trades) * 100) if trades else 0.0

            # Get open positions
            positions_result = await db.execute(
                select(func.count(Order.id)).where(
                    Order.user_id == user.id,
                    Order.status == "OPEN"
                )
            )
            open_positions = positions_result.scalar() or 0

            user_data.append({
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "is_active": user.is_active,
                "session_active": session is not None,
                "total_trades": len(trades),
                "profit_loss": round(total_pl, 2),
                "win_rate": round(win_rate, 2),
                "open_positions": open_positions
            })

        return {
            "total_users": len(users),
            "users": user_data
        }

    except Exception as e:
        logger.error(f"Failed to get users dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get users dashboard: {str(e)}"
        )
