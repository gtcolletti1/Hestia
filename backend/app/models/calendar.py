from typing import Optional

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CalendarProvider(str, enum.Enum):
    local = "local"
    google = "google"
    outlook = "outlook"
    caldav = "caldav"
    ical = "ical"


class SourceCalendar(Base):
    __tablename__ = "source_calendars"

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
    provider: Mapped[CalendarProvider] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True, comment="Override color (hex)"
    )
    is_read_only: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_visible: Mapped[bool] = mapped_column(default=True, nullable=False)
    sync_token: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    household: Mapped["Household"] = relationship(  # noqa: F821
        foreign_keys=[household_id]
    )
    profile: Mapped[Optional["Profile"]] = relationship(  # noqa: F821
        foreign_keys=[profile_id]
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="source_calendar", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<SourceCalendar id={self.id} name={self.name!r} "
            f"provider={self.provider.value}>"
        )


class Event(Base):
    __tablename__ = "events"

    __table_args__ = (
        Index("ix_events_sync_lookup", "source_calendar_id", "external_id"),
        Index("ix_events_time_range", "start_time", "end_time"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_calendar_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    master_external_id: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Parent UID — same as external_id for masters; UID part for overrides",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    all_day: Mapped[bool] = mapped_column(default=False, nullable=False)
    recurrence_rule: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="iCal RRULE string"
    )
    recurrence_id: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC instant of overridden master occurrence (override rows only)",
    )
    exdates: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated UTC ISO datetimes of cancelled master occurrences",
    )
    start_tzid: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="IANA tz of master DTSTART, used for DST-correct RRULE expansion",
    )
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    is_private: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="Hidden in privacy mode"
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    source_calendar: Mapped["SourceCalendar"] = relationship(back_populates="events")
    profile: Mapped[Optional["Profile"]] = relationship(foreign_keys=[profile_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<Event id={self.id} title={self.title!r} start={self.start_time}>"
