"""
Session Manager

Manages multiple user sessions for Match-Trade platform
Handles login, token refresh, and session health monitoring
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.services.mt_api_client import MatchTradeAPIClient, MatchTradeAPIError
from app.models import User, UserSession
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions for multi-account trading

    Features:
    - Concurrent user login
    - Automatic token refresh
    - Session health monitoring
    - Session pool management
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize Session Manager

        Args:
            db: Database session
        """
        self.db = db
        self.api_client = MatchTradeAPIClient()
        self.active_sessions: Dict[int, dict] = {}  # user_id -> session_data
        self.refresh_interval = settings.SESSION_REFRESH_INTERVAL_MINUTES
        self.max_retry_attempts = settings.SESSION_MAX_RETRY_ATTEMPTS

    async def login_all_users(self) -> Dict[str, any]:
        """
        Login all active users concurrently

        Returns:
            Dictionary with login results
        """
        logger.info("Starting login for all users...")

        # Get all active users
        result = await self.db.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()

        if not users:
            logger.warning("No active users found")
            return {
                "success": True,
                "total_users": 0,
                "successful_logins": 0,
                "failed_logins": 0,
                "results": []
            }

        # Login all users concurrently
        tasks = [self.login_user(user.id) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful

        logger.info(f"Login completed: {successful} successful, {failed} failed out of {len(users)} users")

        return {
            "success": True,
            "total_users": len(users),
            "successful_logins": successful,
            "failed_logins": failed,
            "results": [r if isinstance(r, dict) else {"success": False, "error": str(r)} for r in results]
        }

    async def login_user(
        self,
        user_id: int,
        retry_count: int = 0
    ) -> Dict[str, any]:
        """
        Login a specific user

        Args:
            user_id: User ID to login
            retry_count: Current retry attempt

        Returns:
            Login result with session data
        """
        try:
            # Get user from database
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "User not found"
                }

            if not user.is_active:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "User is not active"
                }

            logger.info(f"Logging in user: {user.email}")

            # Decrypt password (in production, use proper encryption)
            from app.utils.encryption import decrypt_sensitive_data
            password = decrypt_sensitive_data(user.encrypted_password)

            # Login via API
            login_response = await self.api_client.login(
                email=user.email,
                password=password,
                broker_id=user.broker_id
            )

            # Extract tokens
            token = login_response.get("token")
            trading_api_token = login_response.get("trading_api_token") or login_response.get("tradingApiToken")
            trading_account_id = login_response.get("trading_account_id") or login_response.get("tradingAccountId")

            if not token or not trading_api_token:
                raise MatchTradeAPIError("Missing tokens in login response")

            # Create or update session in database
            expires_at = datetime.utcnow() + timedelta(minutes=15)

            # Check if session exists
            session_result = await self.db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
            existing_session = session_result.scalar_one_or_none()

            if existing_session:
                # Update existing session
                existing_session.token = token
                existing_session.trading_api_token = trading_api_token
                existing_session.trading_account_id = trading_account_id
                existing_session.login_at = datetime.utcnow()
                existing_session.expires_at = expires_at
                existing_session.is_active = True
                session = existing_session
            else:
                # Create new session
                session = UserSession(
                    user_id=user_id,
                    token=token,
                    trading_api_token=trading_api_token,
                    trading_account_id=trading_account_id,
                    login_at=datetime.utcnow(),
                    expires_at=expires_at,
                    is_active=True
                )
                self.db.add(session)

            try:
                await self.db.commit()
                await self.db.refresh(session)
            except Exception as commit_error:
                await self.db.rollback()
                logger.error(f"Failed to commit session for user {user_id}: {commit_error}")
                raise

            # Add to active sessions cache
            self.active_sessions[user_id] = {
                "user_id": user_id,
                "email": user.email,
                "session_id": session.id,
                "token": token,
                "trading_api_token": trading_api_token,
                "trading_account_id": trading_account_id,
                "login_at": session.login_at,
                "expires_at": expires_at
            }

            logger.info(f"Login successful for user: {user.email}")

            return {
                "success": True,
                "user_id": user_id,
                "email": user.email,
                "session_id": session.id,
                "trading_account_id": trading_account_id,
                "login_at": session.login_at.isoformat()
            }

        except MatchTradeAPIError as e:
            logger.error(f"Login failed for user {user_id}: {e}")

            # Retry logic
            if retry_count < self.max_retry_attempts:
                logger.info(f"Retrying login for user {user_id} (attempt {retry_count + 1}/{self.max_retry_attempts})")
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self.login_user(user_id, retry_count + 1)

            return {
                "success": False,
                "user_id": user_id,
                "error": str(e),
                "retry_count": retry_count
            }

        except Exception as e:
            logger.error(f"Unexpected error during login for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def logout_user(self, user_id: int) -> Dict[str, any]:
        """
        Logout a specific user

        Args:
            user_id: User ID to logout

        Returns:
            Logout result
        """
        try:
            logger.info(f"Logging out user: {user_id}")

            # Get active session
            result = await self.db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "No active session found"
                }

            # Logout via API
            await self.api_client.logout(session.token)

            # Deactivate session in database
            session.is_active = False
            try:
                await self.db.commit()
            except Exception as commit_error:
                await self.db.rollback()
                logger.error(f"Failed to commit logout for user {user_id}: {commit_error}")
                raise

            # Remove from active sessions cache
            if user_id in self.active_sessions:
                del self.active_sessions[user_id]

            logger.info(f"Logout successful for user: {user_id}")

            return {
                "success": True,
                "user_id": user_id
            }

        except Exception as e:
            logger.error(f"Logout failed for user {user_id}: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def refresh_token(self, user_id: int) -> Dict[str, any]:
        """
        Refresh token for a specific user

        Args:
            user_id: User ID

        Returns:
            Refresh result
        """
        try:
            logger.info(f"Refreshing token for user: {user_id}")

            # Get active session
            result = await self.db.execute(
                select(UserSession).where(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.warning(f"No active session for user {user_id}, attempting re-login")
                return await self.login_user(user_id)

            # Refresh token via API
            refresh_response = await self.api_client.refresh_token(session.token)

            # Update session
            new_token = refresh_response.get("token")
            new_trading_token = refresh_response.get("trading_api_token") or refresh_response.get("tradingApiToken")

            if new_token:
                session.token = new_token
            if new_trading_token:
                session.trading_api_token = new_trading_token

            session.last_refresh_at = datetime.utcnow()
            session.expires_at = datetime.utcnow() + timedelta(minutes=15)

            try:
                await self.db.commit()
            except Exception as commit_error:
                await self.db.rollback()
                logger.error(f"Failed to commit token refresh for user {user_id}: {commit_error}")
                raise

            # Update cache
            if user_id in self.active_sessions:
                self.active_sessions[user_id]["token"] = new_token or session.token
                self.active_sessions[user_id]["trading_api_token"] = new_trading_token or session.trading_api_token
                self.active_sessions[user_id]["expires_at"] = session.expires_at

            logger.info(f"Token refreshed successfully for user: {user_id}")

            return {
                "success": True,
                "user_id": user_id,
                "refreshed_at": session.last_refresh_at.isoformat()
            }

        except MatchTradeAPIError as e:
            logger.error(f"Token refresh failed for user {user_id}: {e}")
            # If refresh fails, try re-login
            logger.info(f"Attempting re-login for user {user_id}")
            return await self.login_user(user_id)

        except Exception as e:
            logger.error(f"Unexpected error during token refresh for user {user_id}: {e}")
            return {
                "success": False,
                "user_id": user_id,
                "error": str(e)
            }

    async def refresh_all_tokens(self) -> Dict[str, any]:
        """
        Refresh tokens for all active sessions

        Returns:
            Refresh results
        """
        logger.info("Refreshing tokens for all active sessions...")

        # Get all active sessions
        result = await self.db.execute(
            select(UserSession).where(UserSession.is_active == True)
        )
        sessions = result.scalars().all()

        if not sessions:
            logger.info("No active sessions to refresh")
            return {
                "success": True,
                "total_sessions": 0,
                "successful_refreshes": 0,
                "failed_refreshes": 0
            }

        # Refresh all tokens concurrently
        tasks = [self.refresh_token(session.user_id) for session in sessions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes and failures
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful

        logger.info(f"Token refresh completed: {successful} successful, {failed} failed out of {len(sessions)} sessions")

        return {
            "success": True,
            "total_sessions": len(sessions),
            "successful_refreshes": successful,
            "failed_refreshes": failed
        }

    async def check_session_health(self) -> Dict[str, any]:
        """
        Check health of all active sessions

        Returns:
            Session health report
        """
        logger.info("Checking session health...")

        # Get all active sessions
        result = await self.db.execute(
            select(UserSession).where(UserSession.is_active == True)
        )
        sessions = result.scalars().all()

        healthy_sessions = []
        expiring_soon = []
        expired_sessions = []

        now = datetime.utcnow()

        for session in sessions:
            if session.expires_at:
                time_until_expiry = (session.expires_at - now).total_seconds()

                if time_until_expiry <= 0:
                    expired_sessions.append(session.user_id)
                elif time_until_expiry <= 300:  # Expires in 5 minutes
                    expiring_soon.append(session.user_id)
                else:
                    healthy_sessions.append(session.user_id)

        # Auto-refresh expiring sessions
        if expiring_soon:
            logger.info(f"Auto-refreshing {len(expiring_soon)} sessions expiring soon")
            refresh_tasks = [self.refresh_token(user_id) for user_id in expiring_soon]
            await asyncio.gather(*refresh_tasks, return_exceptions=True)

        # Deactivate expired sessions
        if expired_sessions:
            logger.warning(f"Deactivating {len(expired_sessions)} expired sessions")
            for user_id in expired_sessions:
                await self.db.execute(
                    update(UserSession)
                    .where(UserSession.user_id == user_id, UserSession.is_active == True)
                    .values(is_active=False)
                )
            try:
                await self.db.commit()
            except Exception as commit_error:
                await self.db.rollback()
                logger.error(f"Failed to commit expired session deactivation: {commit_error}")
                # Continue despite error to not block health check

        return {
            "total_sessions": len(sessions),
            "healthy": len(healthy_sessions),
            "expiring_soon": len(expiring_soon),
            "expired": len(expired_sessions),
            "healthy_user_ids": healthy_sessions,
            "expiring_user_ids": expiring_soon,
            "expired_user_ids": expired_sessions
        }

    async def get_active_sessions(self) -> List[Dict[str, any]]:
        """
        Get all active sessions

        Returns:
            List of active session data
        """
        result = await self.db.execute(
            select(UserSession)
            .where(UserSession.is_active == True)
            .join(User)
        )
        sessions = result.scalars().all()

        return [
            {
                "session_id": session.id,
                "user_id": session.user_id,
                "trading_account_id": session.trading_account_id,
                "login_at": session.login_at.isoformat() if session.login_at else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
                "last_refresh_at": session.last_refresh_at.isoformat() if session.last_refresh_at else None
            }
            for session in sessions
        ]

    async def get_session_by_user_id(self, user_id: int) -> Optional[Dict[str, any]]:
        """
        Get active session for a specific user

        Args:
            user_id: User ID

        Returns:
            Session data or None
        """
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        return {
            "session_id": session.id,
            "user_id": session.user_id,
            "token": session.token,
            "trading_api_token": session.trading_api_token,
            "trading_account_id": session.trading_account_id,
            "login_at": session.login_at.isoformat() if session.login_at else None,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None
        }

    async def close(self):
        """Close API client"""
        await self.api_client.close()
