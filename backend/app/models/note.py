"""SQLAlchemy model for family message board notes."""

import uuid
import datetime as dt

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(UUID(as_uuid=True), ForeignKey("households.id"), nullable=False, index=True)
    author_profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False, default="")
    color = Column(String(7), nullable=False, default="#FBBF24")  # hex color
    pinned = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)
