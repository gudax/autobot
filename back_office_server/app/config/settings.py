"""
Configuration settings for Back Office Server
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings"""
    model_config = ConfigDict(extra='ignore')

    # Application
    APP_NAME: str = "Match-Trade Back Office Server"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "trading_system"
    DB_USER: str = "admin"
    DB_PASSWORD: str = ""

    # Match-Trade API
    API_BASE_URL: str = "https://mtr-demo-prod.match-trader.com"
    MATCH_TRADE_BROKER_ID: str = ""

    # Trading Engine
    TRADING_ENGINE_URL: str = "http://localhost:8001"

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Encryption key for sensitive data (passwords, tokens)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: Optional[str] = None  # Set via environment variable in production

    # Session Management
    SESSION_REFRESH_INTERVAL_MINUTES: int = 10
    SESSION_MAX_RETRY_ATTEMPTS: int = 3

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/back_office.log"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database connection URL (for Alembic)"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
