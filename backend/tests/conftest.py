"""Shared test fixtures for the Family Hub backend test suite.

Uses SQLite in-memory via aiosqlite so tests never need PostgreSQL.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.models.user import Household, Profile, ProfileRole

# ---------------------------------------------------------------------------
# SQLite-compatible async engine
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Enable SQLite foreign-key enforcement
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Crypto helper (matches app.api.auth)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_SECRET_KEY = "test-secret-key"
ALGORITHM = "HS256"


def _create_test_token(profile_id: uuid.UUID, role: str = "admin") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(profile_id), "role": role, "exp": expire},
        TEST_SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ---------------------------------------------------------------------------
# Settings override
# ---------------------------------------------------------------------------

def _settings_override() -> Settings:
    return Settings(
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_USER="test",
        POSTGRES_PASSWORD="test",
        POSTGRES_DB="familyhub_test",
        REDIS_URL="redis://localhost:6379/1",
        SECRET_KEY=TEST_SECRET_KEY,
        ALGORITHM=ALGORITHM,
        DEBUG=True,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture()
async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a fresh async session with all tables created, then tear down."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def async_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Async HTTP client wired to the FastAPI app with DB overridden."""
    from app.main import app
    import app.api.auth as auth_module

    override_settings = _settings_override()
    app.dependency_overrides[get_settings] = lambda: override_settings

    # Patch the module-level settings captured at import time in auth
    original_auth_settings = auth_module.settings
    auth_module.settings = override_settings

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    auth_module.settings = original_auth_settings


@pytest_asyncio.fixture()
async def sample_household(db_session: AsyncSession) -> Household:
    """Create and return a test household."""
    household = Household(name="Test Family")
    db_session.add(household)
    await db_session.flush()
    await db_session.refresh(household)
    return household


@pytest_asyncio.fixture()
async def sample_profile(
    db_session: AsyncSession, sample_household: Household
) -> Profile:
    """Create and return an admin profile with a PIN inside sample_household."""
    profile = Profile(
        household_id=sample_household.id,
        name="Admin User",
        color="#FF5733",
        role=ProfileRole.admin,
        pin_hash=pwd_context.hash("1234"),
        is_active=True,
    )
    db_session.add(profile)
    await db_session.flush()
    await db_session.refresh(profile)
    return profile


@pytest_asyncio.fixture()
def auth_headers(sample_profile: Profile) -> dict[str, str]:
    """Return Authorization headers with a valid JWT for sample_profile."""
    token = _create_test_token(sample_profile.id, role=sample_profile.role.value)
    return {"Authorization": f"Bearer {token}"}
