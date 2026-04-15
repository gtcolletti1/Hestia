from collections.abc import AsyncGenerator
import subprocess
import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables and run Alembic migrations."""
    # Ensure all tables exist (safe for first boot)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Run Alembic migrations to apply any schema changes
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Alembic migrations applied successfully")
        else:
            logger.warning("Alembic migration warning: %s", result.stderr)
            # Fallback: apply manual migrations for safety
            await _manual_migrations()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("Alembic not available, running manual migrations")
        await _manual_migrations()


async def _manual_migrations() -> None:
    """Fallback lightweight column migrations (safe to re-run)."""
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text(
                "ALTER TABLE routine_steps ADD COLUMN IF NOT EXISTS points_value INTEGER NOT NULL DEFAULT 0"
            )
        )
