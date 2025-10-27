"""
User schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    broker_id: str
    name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    broker_id: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLoginRequest(BaseModel):
    """Schema for user login request"""
    user_id: int = Field(..., description="User ID to login")


class UserLoginResponse(BaseModel):
    """Schema for user login response"""
    success: bool
    user_id: int
    email: Optional[str] = None
    session_id: Optional[int] = None
    trading_account_id: Optional[str] = None
    login_at: Optional[str] = None
    error: Optional[str] = None


class LoginAllUsersResponse(BaseModel):
    """Schema for login all users response"""
    success: bool
    total_users: int
    successful_logins: int
    failed_logins: int
    results: list
