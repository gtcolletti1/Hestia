"""Pre-login bootstrap/discovery endpoints.

Everything served here is intentionally **unauthenticated** because it has
to be reachable before any user has an opportunity to log in (a fresh
browser opening the kiosk URL needs to know whether setup is required and
which household to join). For that reason the payload is deliberately
minimal — only what the boot flow needs to decide between the setup
wizard, an auto-select, or a household picker.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import Household
from app.schemas.profile import HouseholdSummary, SetupDiscoverResponse

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/discover", response_model=SetupDiscoverResponse)
async def discover(db: AsyncSession = Depends(get_db)) -> SetupDiscoverResponse:
    """Tell the frontend which boot path to take.

    Returns ``setup_required=True`` and an empty list when no household
    exists yet (first-run installs). Otherwise returns the existing
    household(s) so the frontend can auto-select the single one or show a
    picker. Only ``id`` and ``name`` are exposed — never profiles, PINs,
    or settings.
    """
    result = await db.execute(select(Household).order_by(Household.created_at))
    households = list(result.scalars().all())
    return SetupDiscoverResponse(
        setup_required=len(households) == 0,
        households=[HouseholdSummary.model_validate(h) for h in households],
    )
