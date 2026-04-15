"""SQLAlchemy models for the rewards system."""

import uuid
import datetime as dt

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Reward(Base):
    """A reward that can be redeemed with points."""
    __tablename__ = "rewards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    points_cost = Column(Integer, nullable=False, default=10)
    icon = Column(String(50), nullable=True, default="🎁")
    is_active = Column(Integer, nullable=False, default=1)  # SQLite-friendly boolean
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class PointLedger(Base):
    """Append-only ledger tracking point awards and redemptions."""
    __tablename__ = "point_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=False, index=True)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False)  # positive = earned, negative = spent
    reason = Column(String(500), nullable=False)
    routine_step_id = Column(UUID(as_uuid=True), nullable=True)
    reward_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
