"""
Validation utilities
"""

import re
from typing import Optional


def validate_email(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    return True, None


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format

    Args:
        symbol: Trading symbol (e.g., BTCUSD, ETHUSD)

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[A-Z]{3,10}$'
    return re.match(pattern, symbol) is not None


def validate_order_volume(volume: float, min_volume: float = 0.001, max_volume: float = 100.0) -> tuple[bool, Optional[str]]:
    """
    Validate order volume

    Args:
        volume: Order volume
        min_volume: Minimum allowed volume
        max_volume: Maximum allowed volume

    Returns:
        Tuple of (is_valid, error_message)
    """
    if volume < min_volume:
        return False, f"Volume must be at least {min_volume}"

    if volume > max_volume:
        return False, f"Volume must not exceed {max_volume}"

    return True, None


def validate_price(price: float) -> tuple[bool, Optional[str]]:
    """
    Validate price value

    Args:
        price: Price to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if price <= 0:
        return False, "Price must be greater than 0"

    return True, None
