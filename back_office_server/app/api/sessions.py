"""
Session management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.config.database import get_db
from app.schemas import (
    SessionListResponse,
    SessionInfo,
    SessionHealthResponse,
    SuccessResponse
)
from app.services.session_manager import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/", response_model=SessionListResponse)
async def get_active_sessions(db: AsyncSession = Depends(get_db)):
    """
    Get all active sessions

    Returns list of currently active user sessions
    """
    try:
        session_manager = SessionManager(db)
        sessions = await session_manager.get_active_sessions()
        await session_manager.close()

        return SessionListResponse(
            total=len(sessions),
            sessions=[SessionInfo(**session) for session in sessions]
        )

    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sessions: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get session details by ID

    - **session_id**: Session ID
    """
    try:
        session_manager = SessionManager(db)
        # Note: We need to implement get_session_by_id in SessionManager
        # For now, get all sessions and filter
        sessions = await session_manager.get_active_sessions()
        await session_manager.close()

        session = next((s for s in sessions if s["session_id"] == session_id), None)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        return SessionInfo(**session)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


@router.post("/refresh-all", response_model=SuccessResponse)
async def refresh_all_tokens(db: AsyncSession = Depends(get_db)):
    """
    Refresh tokens for all active sessions

    This will refresh authentication tokens for all currently active sessions
    """
    try:
        session_manager = SessionManager(db)
        result = await session_manager.refresh_all_tokens()
        await session_manager.close()

        logger.info(
            f"Token refresh completed: {result['successful_refreshes']}/{result['total_sessions']} successful"
        )

        return SuccessResponse(
            success=True,
            message=f"Refreshed {result['successful_refreshes']} out of {result['total_sessions']} sessions",
            data=result
        )

    except Exception as e:
        logger.error(f"Failed to refresh all tokens: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh tokens: {str(e)}"
        )


@router.delete("/{session_id}", response_model=SuccessResponse)
async def close_session(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Close a specific session

    - **session_id**: Session ID to close
    """
    try:
        # Get session to find user_id
        session_manager = SessionManager(db)
        sessions = await session_manager.get_active_sessions()

        session = next((s for s in sessions if s["session_id"] == session_id), None)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )

        # Logout user
        result = await session_manager.logout_user(session["user_id"])
        await session_manager.close()

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Failed to close session")
            )

        return SuccessResponse(
            success=True,
            message=f"Session {session_id} closed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close session: {str(e)}"
        )


@router.get("/health/check", response_model=SessionHealthResponse)
async def check_session_health(db: AsyncSession = Depends(get_db)):
    """
    Check health of all active sessions

    Returns:
    - Number of healthy sessions
    - Number of sessions expiring soon
    - Number of expired sessions
    - Automatically refreshes expiring sessions
    """
    try:
        session_manager = SessionManager(db)
        health_report = await session_manager.check_session_health()
        await session_manager.close()

        return SessionHealthResponse(**health_report)

    except Exception as e:
        logger.error(f"Failed to check session health: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check session health: {str(e)}"
        )
