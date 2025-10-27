"""
Trading API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from app.config.database import get_db
from app.models import Order, Trade
from app.schemas import (
    TradingSignalRequest,
    ExecuteSignalResponse,
    ClosePositionsRequest,
    ClosePositionsResponse,
    PositionListResponse,
    OrderInfo,
    TradeInfo
)
from app.services.order_orchestrator import OrderOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])


@router.post("/signal", response_model=ExecuteSignalResponse)
async def execute_trading_signal(
    signal: TradingSignalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a trading signal for all active users

    - **action**: OPEN_LONG, OPEN_SHORT, CLOSE, or CLOSE_ALL
    - **symbol**: Trading symbol (e.g., BTCUSD)
    - **entry_price**: Entry price
    - **stop_loss**: Stop loss price
    - **take_profit**: Take profit price
    - **volume**: Order volume
    - **reason**: Signal reason/description
    """
    try:
        logger.info(f"Received trading signal: {signal.action} {signal.symbol}")

        orchestrator = OrderOrchestrator(db)
        result = await orchestrator.execute_signal_for_all(signal.dict())
        await orchestrator.close()

        return ExecuteSignalResponse(**result)

    except Exception as e:
        logger.error(f"Failed to execute trading signal: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute signal: {str(e)}"
        )


@router.post("/execute-all", response_model=ExecuteSignalResponse)
async def execute_orders_for_all(
    signal: TradingSignalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute orders for all active users (alias for /signal)

    - **action**: OPEN_LONG, OPEN_SHORT, CLOSE, or CLOSE_ALL
    - **symbol**: Trading symbol
    - **entry_price**: Entry price
    - **stop_loss**: Stop loss price
    - **take_profit**: Take profit price
    - **volume**: Order volume
    """
    return await execute_trading_signal(signal, db)


@router.get("/positions", response_model=PositionListResponse)
async def get_open_positions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all open positions across all users

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        result = await db.execute(
            select(Order)
            .where(Order.status == "OPEN")
            .offset(skip)
            .limit(limit)
        )
        orders = result.scalars().all()

        return PositionListResponse(
            total=len(orders),
            positions=[OrderInfo.from_orm(order) for order in orders]
        )

    except Exception as e:
        logger.error(f"Failed to get open positions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )


@router.get("/positions/user/{user_id}", response_model=PositionListResponse)
async def get_user_positions(
    user_id: int,
    status_filter: str = "OPEN",
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get positions for a specific user

    - **user_id**: User ID
    - **status_filter**: Filter by status (OPEN, CLOSED, etc.)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        query = select(Order).where(Order.user_id == user_id)

        if status_filter:
            query = query.where(Order.status == status_filter)

        result = await db.execute(
            query.offset(skip).limit(limit)
        )
        orders = result.scalars().all()

        return PositionListResponse(
            total=len(orders),
            positions=[OrderInfo.from_orm(order) for order in orders]
        )

    except Exception as e:
        logger.error(f"Failed to get positions for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user positions: {str(e)}"
        )


@router.post("/close-all", response_model=ClosePositionsResponse)
async def close_all_positions(
    request: ClosePositionsRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Close all open positions

    - **symbol**: Optional - close positions for specific symbol only
    - **user_ids**: Optional - close positions for specific users only
    """
    try:
        orchestrator = OrderOrchestrator(db)

        # Create close signal
        signal = {
            "action": "CLOSE",
            "symbol": request.symbol if request else None
        }

        result = await orchestrator.execute_signal_for_all(signal)
        await orchestrator.close()

        return ClosePositionsResponse(
            success=result.get("success", True),
            closed_count=result.get("executed_count", 0),
            failed_count=result.get("failed_count", 0),
            results=result.get("successful_orders", []) + result.get("failed_orders", [])
        )

    except Exception as e:
        logger.error(f"Failed to close all positions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close positions: {str(e)}"
        )


@router.get("/orders", response_model=List[OrderInfo])
async def get_orders(
    status_filter: str = None,
    symbol: str = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get order history

    - **status_filter**: Filter by status (OPEN, CLOSED, PENDING, etc.)
    - **symbol**: Filter by symbol
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        query = select(Order)

        if status_filter:
            query = query.where(Order.status == status_filter)
        if symbol:
            query = query.where(Order.symbol == symbol)

        result = await db.execute(
            query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        )
        orders = result.scalars().all()

        return [OrderInfo.from_orm(order) for order in orders]

    except Exception as e:
        logger.error(f"Failed to get orders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )


@router.get("/trades", response_model=List[TradeInfo])
async def get_trades(
    user_id: int = None,
    symbol: str = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get trade history

    - **user_id**: Filter by user ID
    - **symbol**: Filter by symbol
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        query = select(Trade)

        if user_id:
            query = query.where(Trade.user_id == user_id)
        if symbol:
            query = query.where(Trade.symbol == symbol)

        result = await db.execute(
            query.order_by(Trade.closed_at.desc()).offset(skip).limit(limit)
        )
        trades = result.scalars().all()

        return [TradeInfo.from_orm(trade) for trade in trades]

    except Exception as e:
        logger.error(f"Failed to get trades: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trades: {str(e)}"
        )


@router.get("/trades/today", response_model=List[TradeInfo])
async def get_today_trades(
    db: AsyncSession = Depends(get_db)
):
    """Get trades from today"""
    try:
        from datetime import datetime, timedelta

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = await db.execute(
            select(Trade)
            .where(Trade.closed_at >= today_start)
            .order_by(Trade.closed_at.desc())
        )
        trades = result.scalars().all()

        return [TradeInfo.from_orm(trade) for trade in trades]

    except Exception as e:
        logger.error(f"Failed to get today's trades: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get today's trades: {str(e)}"
        )
