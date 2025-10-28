"""
Global settings for Trading Engine
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from environment
    )

    # Application Configuration
    app_env: str = "development"
    
    # Back Office API Configuration
    back_office_api_url: str = "http://localhost:8000"

    # Match-Trade API Configuration
    api_base_url: str = "https://mtr-demo-prod.match-trader.com"
    api_timeout: int = 30
    api_retry_attempts: int = 3
    api_retry_delay: int = 1

    # Trading Configuration
    trading_enabled: bool = True
    max_concurrent_requests: int = 10

    # Market Data Configuration
    candle_timeframes: list[str] = ["1m", "5m", "15m"]
    data_refresh_interval: int = 1  # seconds

    # WebSocket Configuration
    ws_reconnect_attempts: int = 5
    ws_reconnect_delay: int = 3
    ws_ping_interval: int = 30

    # Database Configuration
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "trading_system"
    db_user: str = "admin"
    db_password: str = ""

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = "logs/trading_engine.log"

    # Risk Management
    max_position_size: float = 0.1
    max_positions_per_symbol: int = 3
    max_total_positions: int = 10
    risk_per_trade: float = 0.01  # 1% of account

    # Cache Configuration
    cache_enabled: bool = True
    cache_ttl: int = 60  # seconds

    @property
    def database_url(self) -> str:
        """Construct database URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        """Construct async database URL"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Global settings instance
settings = Settings()
