import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("Family Hub API starting up")
    # Import all models so Base.metadata knows every table, then create them.
    import app.models  # noqa: F401
    from app.database import init_db
    await init_db()
    logger.info("Database tables ready")
    yield
    logger.info("Family Hub API shutting down")


app = FastAPI(
    title="Family Hub API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ─────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


# ── Router includes ──────────────────────────────────────────────────────────

from app.api import calendar, lists, profiles, routines  # noqa: E402

app.include_router(profiles.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(routines.router, prefix="/api")
app.include_router(lists.router, prefix="/api")

from app.api import integrations  # noqa: E402

app.include_router(integrations.router, prefix="/api")

from app.api import admin, auth, dashboard, meals, weather  # noqa: E402
from app.api import photos  # noqa: E402
from app.api import notes  # noqa: E402

app.include_router(auth.router, prefix="/api")
app.include_router(meals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
