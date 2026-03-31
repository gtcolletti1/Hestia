from typing import Optional

import enum
import uuid
from datetime import date, datetime, time

from sqlalchemy import Date, ForeignKey, String, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimeBlock(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
    bedtime = "bedtime"


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    time_block: Mapped[TimeBlock] = mapped_column(nullable=False)
    days_of_week: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="Array of day numbers, e.g. [0,1,2,3,4]"
    )
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    household: Mapped["Household"] = relationship(foreign_keys=[household_id])  # noqa: F821
    profile: Mapped[Optional["Profile"]] = relationship(foreign_keys=[profile_id])  # noqa: F821
    steps: Mapped[list["RoutineStep"]] = relationship(
        back_populates="routine", cascade="all, delete-orphan", order_by="RoutineStep.sort_order"
    )
    completions: Mapped[list["RoutineCompletion"]] = relationship(
        back_populates="routine", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Routine id={self.id} name={self.name!r} time_block={self.time_block.value}>"


class RoutineStep(Base):
    __tablename__ = "routine_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    routine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routines.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Emoji or icon name"
    )
    sort_order: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )

    # Relationships
    routine: Mapped["Routine"] = relationship(back_populates="steps")

    def __repr__(self) -> str:
        return f"<RoutineStep id={self.id} label={self.label!r} order={self.sort_order}>"


class RoutineCompletion(Base):
    __tablename__ = "routine_completions"

    __table_args__ = (
        UniqueConstraint("routine_id", "profile_id", "date", name="uq_routine_completion_per_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    routine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routines.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_steps: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="Array of completed step UUIDs"
    )
    is_fully_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )

    # Relationships
    routine: Mapped["Routine"] = relationship(back_populates="completions")
    profile: Mapped["Profile"] = relationship(foreign_keys=[profile_id])  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<RoutineCompletion id={self.id} routine_id={self.routine_id} "
            f"date={self.date} completed={self.is_fully_completed}>"
        )
