"""
Helper functions for Trading Engine
"""

from typing import Union, Optional
from decimal import Decimal, ROUND_DOWN
import pandas as pd
from datetime import datetime, timedelta


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
    leverage: int = 1
) -> float:
    """
    Calculate position size based on risk management

    Args:
        account_balance: Account balance in USD
        risk_percent: Risk percentage (0.01 = 1%)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        leverage: Leverage multiplier

    Returns:
        Position size in lots/contracts
    """
    risk_amount = account_balance * risk_percent
    price_difference = abs(entry_price - stop_loss_price)

    if price_difference == 0:
        return 0.0

    position_size = (risk_amount / price_difference) * leverage
    return round(position_size, 8)


def calculate_stop_loss(
    entry_price: float,
    side: str,
    stop_loss_percent: float
) -> float:
    """
    Calculate stop loss price

    Args:
        entry_price: Entry price
        side: Position side (LONG or SHORT)
        stop_loss_percent: Stop loss percentage (0.002 = 0.2%)

    Returns:
        Stop loss price
    """
    if side.upper() == "LONG":
        stop_loss = entry_price * (1 - stop_loss_percent)
    else:  # SHORT
        stop_loss = entry_price * (1 + stop_loss_percent)

    return round(stop_loss, 2)


def calculate_take_profit(
    entry_price: float,
    side: str,
    take_profit_percent: float
) -> float:
    """
    Calculate take profit price

    Args:
        entry_price: Entry price
        side: Position side (LONG or SHORT)
        take_profit_percent: Take profit percentage (0.003 = 0.3%)

    Returns:
        Take profit price
    """
    if side.upper() == "LONG":
        take_profit = entry_price * (1 + take_profit_percent)
    else:  # SHORT
        take_profit = entry_price * (1 - take_profit_percent)

    return round(take_profit, 2)


def calculate_profit_loss(
    entry_price: float,
    exit_price: float,
    side: str,
    quantity: float
) -> tuple[float, float]:
    """
    Calculate profit/loss amount and percentage

    Args:
        entry_price: Entry price
        exit_price: Exit price
        side: Position side (LONG or SHORT)
        quantity: Position quantity

    Returns:
        Tuple of (profit_loss_amount, profit_loss_percent)
    """
    if side.upper() == "LONG":
        profit_loss = (exit_price - entry_price) * quantity
        profit_loss_percent = ((exit_price - entry_price) / entry_price) * 100
    else:  # SHORT
        profit_loss = (entry_price - exit_price) * quantity
        profit_loss_percent = ((entry_price - exit_price) / entry_price) * 100

    return round(profit_loss, 2), round(profit_loss_percent, 4)


def format_price(price: Union[float, Decimal], decimals: int = 2) -> str:
    """
    Format price for display

    Args:
        price: Price value
        decimals: Number of decimal places

    Returns:
        Formatted price string
    """
    return f"${price:,.{decimals}f}"


def format_volume(volume: Union[float, Decimal], decimals: int = 4) -> str:
    """
    Format volume for display

    Args:
        volume: Volume value
        decimals: Number of decimal places

    Returns:
        Formatted volume string
    """
    return f"{volume:.{decimals}f}"


def format_percent(value: float, decimals: int = 2) -> str:
    """
    Format percentage for display

    Args:
        value: Percentage value (as decimal, e.g., 0.05 = 5%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    percent = value * 100 if abs(value) < 1 else value
    sign = "+" if percent > 0 else ""
    return f"{sign}{percent:.{decimals}f}%"


def calculate_moving_average(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate simple moving average

    Args:
        data: Data series
        period: Moving average period

    Returns:
        Moving average series
    """
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate exponential moving average

    Args:
        data: Data series
        period: EMA period

    Returns:
        EMA series
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)

    Args:
        data: Price data series
        period: RSI period

    Returns:
        RSI series
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def is_within_trading_hours(
    current_time: Optional[datetime] = None,
    start_hour: int = 0,
    end_hour: int = 24
) -> bool:
    """
    Check if current time is within trading hours

    Args:
        current_time: Time to check (defaults to now)
        start_hour: Trading start hour (UTC)
        end_hour: Trading end hour (UTC)

    Returns:
        True if within trading hours
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_hour = current_time.hour
    return start_hour <= current_hour < end_hour


def calculate_duration(start_time: datetime, end_time: Optional[datetime] = None) -> int:
    """
    Calculate duration in seconds

    Args:
        start_time: Start time
        end_time: End time (defaults to now)

    Returns:
        Duration in seconds
    """
    if end_time is None:
        end_time = datetime.utcnow()

    duration = end_time - start_time
    return int(duration.total_seconds())


def format_duration(seconds: int) -> str:
    """
    Format duration for display

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 30s")
    """
    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes > 0:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format

    Args:
        symbol: Trading symbol

    Returns:
        True if valid
    """
    if not symbol or len(symbol) < 3:
        return False

    return symbol.isalnum() and symbol.isupper()


def round_to_tick_size(price: float, tick_size: float = 0.01) -> float:
    """
    Round price to nearest tick size

    Args:
        price: Price to round
        tick_size: Tick size (e.g., 0.01 for 2 decimals)

    Returns:
        Rounded price
    """
    return round(price / tick_size) * tick_size
