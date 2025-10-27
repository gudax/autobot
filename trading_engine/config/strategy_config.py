"""
Strategy parameters and configuration
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class VolumeAnalysisConfig:
    """Volume analysis parameters"""

    # Moving average periods for volume
    ma_periods: list[int] = None

    # Volume spike thresholds (multiplier of average)
    spike_threshold_low: float = 2.0
    spike_threshold_medium: float = 3.0
    spike_threshold_high: float = 5.0

    # Buy/Sell ratio thresholds
    buy_sell_ratio_threshold: float = 0.6

    # Minimum consecutive candles in same direction
    min_consecutive_candles: int = 3

    def __post_init__(self):
        if self.ma_periods is None:
            self.ma_periods = [20, 50, 100]


@dataclass
class OrderBookConfig:
    """Order book analysis parameters"""

    # Number of order book levels to analyze
    order_book_depth: int = 10

    # Imbalance ratio threshold (>0.5 = buy pressure)
    imbalance_threshold: float = 0.6

    # Large order detection (percentage of total volume)
    large_order_threshold: float = 0.2

    # Spread threshold in basis points
    max_spread_bps: int = 20

    # Liquidity score threshold (0-1)
    min_liquidity_score: float = 0.5


@dataclass
class ScalpingConfig:
    """Scalping strategy parameters"""

    # Entry conditions
    volume_spike_required: bool = True
    orderbook_imbalance_required: bool = True
    chart_pattern_required: bool = False

    # Technical indicators
    use_rsi: bool = True
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    use_moving_average: bool = True
    ma_period: int = 20

    # Signal strength threshold (0-1)
    min_signal_strength: float = 0.7

    # Exit conditions
    take_profit_percent: float = 0.3  # 0.3%
    stop_loss_percent: float = 0.2    # 0.2%

    # Alternative exit conditions
    max_hold_time_seconds: int = 300  # 5 minutes
    trailing_stop_enabled: bool = False
    trailing_stop_percent: float = 0.15

    # Position management
    position_size_percent: float = 0.02  # 2% of account per trade
    leverage: int = 10

    # Timeframes to analyze
    primary_timeframe: str = "1m"
    confirmation_timeframes: list[str] = None

    def __post_init__(self):
        if self.confirmation_timeframes is None:
            self.confirmation_timeframes = ["5m", "15m"]


@dataclass
class RiskManagementConfig:
    """Risk management parameters"""

    # Maximum risk per trade (percentage of account)
    max_risk_per_trade: float = 0.01  # 1%

    # Maximum total risk (all open positions)
    max_total_risk: float = 0.05  # 5%

    # Maximum positions
    max_positions_per_symbol: int = 1
    max_total_positions: int = 5

    # Drawdown limits
    max_daily_drawdown: float = 0.03  # 3%
    max_total_drawdown: float = 0.10  # 10%

    # Trading hours (UTC)
    trading_start_hour: int = 0
    trading_end_hour: int = 24

    # Emergency stop
    emergency_stop_enabled: bool = True
    emergency_stop_loss_threshold: float = 0.05  # 5% account loss


class StrategyConfig:
    """Complete strategy configuration"""

    def __init__(
        self,
        volume_config: VolumeAnalysisConfig = None,
        orderbook_config: OrderBookConfig = None,
        scalping_config: ScalpingConfig = None,
        risk_config: RiskManagementConfig = None
    ):
        self.volume = volume_config or VolumeAnalysisConfig()
        self.orderbook = orderbook_config or OrderBookConfig()
        self.scalping = scalping_config or ScalpingConfig()
        self.risk = risk_config or RiskManagementConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "volume": self.volume.__dict__,
            "orderbook": self.orderbook.__dict__,
            "scalping": self.scalping.__dict__,
            "risk": self.risk.__dict__
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "StrategyConfig":
        """Create configuration from dictionary"""
        return cls(
            volume_config=VolumeAnalysisConfig(**config_dict.get("volume", {})),
            orderbook_config=OrderBookConfig(**config_dict.get("orderbook", {})),
            scalping_config=ScalpingConfig(**config_dict.get("scalping", {})),
            risk_config=RiskManagementConfig(**config_dict.get("risk", {}))
        )


# Default strategy configuration
default_strategy_config = StrategyConfig()
