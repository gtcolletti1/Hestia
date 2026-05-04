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
    pausable_on_vacation: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        server_default="true",
        comment=(
            "If True, household-wide vacation pauses also suspend this "
            "routine. Set False for medication / safety routines that "
            "should never auto-pause."
        ),
    )
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
    points_value: Mapped[int] = mapped_column(default=0, nullable=False, comment="Points awarded on completion")
    days_of_week: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "Optional per-step weekday filter (0=Mon..6=Sun). NULL = applies "
            "on every day the parent routine runs."
        ),
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


class RoutineOverrideKind(str, enum.Enum):
    pause = "pause"
    skip = "skip"


class RoutineOverride(Base):
    """Pause / skip rule that suppresses a routine for a date range.

    A row with ``routine_id IS NULL`` is a household-wide pause (vacation
    mode) that suppresses every routine in the household whose
    ``pausable_on_vacation`` flag is True.

    For ``kind == 'skip'``, ``end_date`` equals ``start_date`` (a single
    day off — typically "skip today" from the routines tab).
    For ``kind == 'pause'``, ``end_date`` is either a future date or NULL
    (indefinite, until cancelled).
    """

    __tablename__ = "routine_overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    routine_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routines.id", ondelete="CASCADE"),
        nullable=True,
    )
    kind: Mapped[RoutineOverrideKind] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )

    routine: Mapped[Optional["Routine"]] = relationship(foreign_keys=[routine_id])

    def covers(self, target: date) -> bool:
        if target < self.start_date:
            return False
        if self.end_date is not None and target > self.end_date:
            return False
        return True

    def __repr__(self) -> str:
        scope = f"routine={self.routine_id}" if self.routine_id else "household-wide"
        end = self.end_date.isoformat() if self.end_date else "indefinite"
        return f"<RoutineOverride {self.kind} {scope} {self.start_date}..{end}>"
