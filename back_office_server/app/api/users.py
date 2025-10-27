"""
User management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from app.config.database import get_db
from app.models import User
from app.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLoginRequest,
    UserLoginResponse,
    LoginAllUsersResponse,
    SuccessResponse,
    ErrorResponse
)
from app.services.session_manager import SessionManager
from app.utils.encryption import hash_password, encrypt_sensitive_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user

    - **email**: User email address
    - **password**: User password (will be encrypted)
    - **broker_id**: Broker ID for Match-Trade platform
    - **name**: Optional user name
    """
    try:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Hash password and encrypt
        encrypted_password = encrypt_sensitive_data(user_data.password)

        # Create new user
        new_user = User(
            email=user_data.email,
            encrypted_password=encrypted_password,
            broker_id=user_data.broker_id,
            name=user_data.name,
            is_active=True
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        logger.info(f"User created: {new_user.email}")

        return new_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all users

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    try:
        result = await db.execute(
            select(User).offset(skip).limit(limit)
        )
        users = result.scalars().all()

        return users

    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID

    - **user_id**: User ID
    """
    try:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update user information

    - **user_id**: User ID
    - **email**: New email (optional)
    - **password**: New password (optional)
    - **broker_id**: New broker ID (optional)
    - **name**: New name (optional)
    - **is_active**: Active status (optional)
    """
    try:
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Update fields
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.password is not None:
            user.encrypted_password = encrypt_sensitive_data(user_data.password)
        if user_data.broker_id is not None:
            user.broker_id = user_data.broker_id
        if user_data.name is not None:
            user.name = user_data.name
        if user_data.is_active is not None:
            user.is_active = user_data.is_active

        await db.commit()
        await db.refresh(user)

        logger.info(f"User updated: {user.email}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user

    - **user_id**: User ID
    """
    try:
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        await db.delete(user)
        await db.commit()

        logger.info(f"User deleted: {user.email}")

        return SuccessResponse(
            success=True,
            message=f"User {user_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.post("/{user_id}/login", response_model=UserLoginResponse)
async def login_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Login a specific user to Match-Trade platform

    - **user_id**: User ID to login
    """
    try:
        session_manager = SessionManager(db)
        result = await session_manager.login_user(user_id)
        await session_manager.close()

        return UserLoginResponse(**result)

    except Exception as e:
        logger.error(f"Failed to login user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to login user: {str(e)}"
        )


@router.post("/{user_id}/logout", response_model=SuccessResponse)
async def logout_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout a specific user from Match-Trade platform

    - **user_id**: User ID to logout
    """
    try:
        session_manager = SessionManager(db)
        result = await session_manager.logout_user(user_id)
        await session_manager.close()

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Logout failed")
            )

        return SuccessResponse(
            success=True,
            message=f"User {user_id} logged out successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to logout user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout user: {str(e)}"
        )


@router.post("/login-all", response_model=LoginAllUsersResponse)
async def login_all_users(db: AsyncSession = Depends(get_db)):
    """
    Login all active users concurrently

    This endpoint will attempt to login all active users to the Match-Trade platform
    simultaneously using async operations for maximum performance.
    """
    try:
        session_manager = SessionManager(db)
        result = await session_manager.login_all_users()
        await session_manager.close()

        logger.info(
            f"Login all completed: {result['successful_logins']}/{result['total_users']} successful"
        )

        return LoginAllUsersResponse(**result)

    except Exception as e:
        logger.error(f"Failed to login all users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to login all users: {str(e)}"
        )
