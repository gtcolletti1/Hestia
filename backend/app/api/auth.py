
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import Profile, ProfileRole

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Schemas ──────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    profile_id: str
    pin: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    profile: dict


class PinRequest(BaseModel):
    profile_id: str
    pin: str


class ProfileOut(BaseModel):
    id: str
    name: str
    role: str
    color: str
    avatar_url: str | None = None
    household_id: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def _create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _profile_to_dict(profile: Profile) -> dict:
    return {
        "id": str(profile.id),
        "name": profile.name,
        "role": profile.role.value,
        "color": profile.color,
        "avatar_url": profile.avatar_url,
        "household_id": str(profile.household_id),
    }


# ── Dependencies ─────────────────────────────────────────────────────────────


async def get_current_profile(
    token: str = Depends(lambda: None),  # replaced below
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """Decode JWT and return the corresponding Profile."""
    ...  # overridden — see the real implementation used via Depends


from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer()


async def get_current_profile(  # noqa: F811
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """Decode the JWT bearer token and return the authenticated Profile."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        profile_id: str | None = payload.get("sub")
        if profile_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Profile).where(Profile.id == _uuid.UUID(profile_id)))
    profile = result.scalar_one_or_none()
    if profile is None or not profile.is_active:
        raise credentials_exception
    return profile


async def require_admin(
    profile: Profile = Depends(get_current_profile),
) -> Profile:
    """Ensure the authenticated profile has the admin role."""
    if profile.role != ProfileRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return profile


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with profile_id + PIN, return a JWT."""
    result = await db.execute(select(Profile).where(Profile.id == _uuid.UUID(body.profile_id)))
    profile = result.scalar_one_or_none()

    if profile is None or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid profile or PIN",
        )

    if not profile.pin_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PIN not set for this profile",
        )

    if not pwd_context.verify(body.pin, profile.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid profile or PIN",
        )

    access_token = _create_access_token(
        data={"sub": str(profile.id), "role": profile.role.value}
    )
    return LoginResponse(
        access_token=access_token,
        profile=_profile_to_dict(profile),
    )


@router.post("/pin", status_code=status.HTTP_204_NO_CONTENT)
async def set_pin(
    body: PinRequest,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
):
    """Set or update the PIN for a profile. Admin can set any; others only their own."""
    is_own = str(current_profile.id) == body.profile_id
    is_admin = current_profile.role == ProfileRole.admin

    if not is_own and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own PIN",
        )

    result = await db.execute(select(Profile).where(Profile.id == _uuid.UUID(body.profile_id)))
    target_profile = result.scalar_one_or_none()
    if target_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    target_profile.pin_hash = pwd_context.hash(body.pin)
    await db.flush()


@router.get("/me", response_model=ProfileOut)
async def get_me(profile: Profile = Depends(get_current_profile)):
    """Return the currently authenticated profile."""
    return ProfileOut(
        id=str(profile.id),
        name=profile.name,
        role=profile.role.value,
        color=profile.color,
        avatar_url=profile.avatar_url,
        household_id=str(profile.household_id),
    )
