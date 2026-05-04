"""Manual school-closure dates (snow days, in-service days, etc.).

Used together with the built-in US federal holiday calendar in
``app.services.school_day`` to decide whether routine steps flagged
``school_day_only`` should run on a given date.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SchoolClosure(Base):
    __tablename__ = "school_closures"

    __table_args__ = (
        UniqueConstraint(
            "household_id", "date", name="uq_school_closure_household_date"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<SchoolClosure household={self.household_id} "
            f"date={self.date} reason={self.reason!r}>"
        )
