"""Database configuration and connection management"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine if running in test mode
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
# For SQLite, connect_args might be needed if using FastAPI/async with threads
SQLITE_CONNECT_ARGS = {"check_same_thread": False} if TEST_MODE else {}


if TEST_MODE:
    # Use SQLite in-memory or file-based for testing
    # Defaulting to a file-based SQLite DB for easier inspection during/after tests
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test_db.sqlite3")
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("ENVIRONMENT", "development") == "development",
        connect_args=SQLITE_CONNECT_ARGS
    )
else:
    # Default to PostgreSQL for development/production
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/time_series_db")
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("ENVIRONMENT", "development") == "development",
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE", "3600")),
    )

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session"""
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
    """Initialize database - create tables"""
    async with engine.begin() as conn:
        # For SQLite, Base.metadata.create_all is sufficient.
        # For Alembic with PostgreSQL, you might have a different migration strategy.
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()