"""API routes for the rewards system."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_profile, require_admin
from app.database import get_db
from app.models.reward import Reward, PointLedger
from app.models.user import Profile
from app.schemas.reward import (
    RewardCreate,
    RewardResponse,
    RewardUpdate,
    PointBalanceResponse,
    LeaderboardEntry,
    RedeemRequest,
    PointLedgerResponse,
)

router = APIRouter(tags=["rewards"])


# ── Rewards CRUD ─────────────────────────────────────────────────────────────


@router.get("/rewards", response_model=list[RewardResponse])
async def list_rewards(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[Reward]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(Reward)
        .where(Reward.household_id == household_id, Reward.is_active == 1)
        .order_by(Reward.points_cost)
    )
    return list(result.scalars().all())


@router.post("/rewards", response_model=RewardResponse, status_code=status.HTTP_201_CREATED)
async def create_reward(
    data: RewardCreate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> Reward:
    if current_profile.household_id != data.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    reward = Reward(**data.model_dump())
    db.add(reward)
    await db.flush()
    await db.refresh(reward)
    return reward


@router.put("/rewards/{reward_id}", response_model=RewardResponse)
async def update_reward(
    reward_id: uuid.UUID,
    data: RewardUpdate,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> Reward:
    reward = await db.get(Reward, reward_id)
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    if reward.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reward, field, value)
    await db.flush()
    await db.refresh(reward)
    return reward


@router.delete("/rewards/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reward(
    reward_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(require_admin),
) -> None:
    reward = await db.get(Reward, reward_id)
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    if reward.household_id != current_profile.household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(reward)
    await db.flush()


# ── Points ───────────────────────────────────────────────────────────────────


@router.get("/rewards/points", response_model=PointBalanceResponse)
async def get_point_balance(
    profile_id: uuid.UUID = Query(...),
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> PointBalanceResponse:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")
    result = await db.execute(
        select(func.coalesce(func.sum(PointLedger.points), 0))
        .where(PointLedger.profile_id == profile_id, PointLedger.household_id == household_id)
    )
    total = result.scalar()
    return PointBalanceResponse(profile_id=profile_id, total_points=total or 0)


@router.get("/rewards/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    household_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> list[LeaderboardEntry]:
    if current_profile.household_id != household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(
            Profile.id,
            Profile.name,
            Profile.avatar_url,
            func.coalesce(func.sum(PointLedger.points), 0).label("total_points"),
        )
        .outerjoin(PointLedger, PointLedger.profile_id == Profile.id)
        .where(Profile.household_id == household_id)
        .group_by(Profile.id, Profile.name, Profile.avatar_url)
        .order_by(func.coalesce(func.sum(PointLedger.points), 0).desc())
    )

    return [
        LeaderboardEntry(
            profile_id=row.id,
            display_name=row.name,
            avatar_url=row.avatar_url,
            total_points=row.total_points,
        )
        for row in result.all()
    ]


@router.post("/rewards/redeem", response_model=PointLedgerResponse)
async def redeem_reward(
    data: RedeemRequest,
    db: AsyncSession = Depends(get_db),
    current_profile: Profile = Depends(get_current_profile),
) -> PointLedger:
    if current_profile.household_id != data.household_id:
        raise HTTPException(status_code=403, detail="Access denied")

    reward = await db.get(Reward, data.reward_id)
    if not reward or reward.household_id != data.household_id:
        raise HTTPException(status_code=404, detail="Reward not found")

    # Check balance
    result = await db.execute(
        select(func.coalesce(func.sum(PointLedger.points), 0))
        .where(PointLedger.profile_id == data.profile_id, PointLedger.household_id == data.household_id)
    )
    balance = result.scalar() or 0

    if balance < reward.points_cost:
        raise HTTPException(status_code=400, detail=f"Not enough points (have {balance}, need {reward.points_cost})")

    entry = PointLedger(
        household_id=data.household_id,
        profile_id=data.profile_id,
        points=-reward.points_cost,
        reason=f"Redeemed: {reward.title}",
        reward_id=reward.id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry
