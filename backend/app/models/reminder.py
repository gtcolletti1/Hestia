"""SQLAlchemy model for event reminders and notifications."""

import uuid
import datetime as dt

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=False, index=True)
    minutes_before = Column(Integer, nullable=False, default=15)
    is_fired = Column(Boolean, nullable=False, default=False)
    fire_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
