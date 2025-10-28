"""
Database configuration and session management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config.settings import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

# Clean the DATABASE_URL - remove any ssl parameters from URL
# We will pass ssl=False via connect_args instead
database_url = settings.database_url
if "?ssl=" in database_url:
    database_url = database_url.split("?")[0]
if "&ssl=" in database_url:
    database_url = database_url.split("&ssl=")[0]

# Create async engine with SSL disabled for asyncpg
engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    poolclass=NullPool,
    future=True,
    connect_args={
        "ssl": False,  # Disable SSL for asyncpg
        "timeout": 60,
        "command_timeout": 60,
        "server_settings": {"jit": "off"}
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create declarative base for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session

    Usage in FastAPI:
        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create all tables with retry logic"""
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to initialize database after {max_retries} attempts: {e}")
                raise


async def close_db():
    """Close database connection"""
    await engine.dispose()
