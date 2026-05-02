from collections.abc import AsyncGenerator
import logging

from sqlalchemy import inspect, text
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


def _run_alembic_command(*args: str) -> None:
    """Invoke an Alembic command in-process so it shares this venv's drivers."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)
    getattr(command, args[0])(cfg, *args[1:])


async def init_db() -> None:
    """Bring the database schema up to the current Alembic head.

    Behavior:
      * Fresh DB (no tables): create the schema, then stamp it as the
        current Alembic head.
      * Existing DB managed by Alembic: run ``alembic upgrade head``.
      * Legacy DB built by ``Base.metadata.create_all`` (no alembic_version
        table but other tables exist): stamp head so future migrations have
        a known starting point. We assume the schema is current.
    """
    # Import all models so Base.metadata is fully populated before we look
    # at the live schema.
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        existing_tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

    has_alembic = "alembic_version" in existing_tables
    has_app_tables = any(t != "alembic_version" for t in existing_tables)

    if has_alembic:
        # Normal path: let Alembic catch the DB up.
        try:
            _run_alembic_command("upgrade", "head")
            logger.info("Alembic upgrade head completed")
        except Exception:  # pragma: no cover - logged for ops visibility
            logger.exception("Alembic upgrade failed")
            raise
        return

    if has_app_tables:
        # Legacy schema produced by an earlier create_all-only boot.
        # Assume it matches current models and just record the head so
        # future migrations apply cleanly.
        logger.warning(
            "Database has app tables but no alembic_version. "
            "Stamping head to bring it under Alembic management."
        )
        _run_alembic_command("stamp", "head")
        return

    # Fresh DB: build the schema from models, then stamp head.
    logger.info("Empty database detected; creating schema and stamping head")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _run_alembic_command("stamp", "head")
