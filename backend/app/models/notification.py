"""Persistent notification inbox — feeds the dashboard bell.

Reminder firing, sync errors, and other household events insert rows here so
that family members can see a history of what's happened (with a per-profile
or household-wide read state).
"""

import datetime as dt
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class NotificationEntry(Base):
    __tablename__ = "notification_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id = Column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # NULL = household-wide notification (every profile sees it).
    # Otherwise: only the named profile sees it in their inbox.
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Free-form short identifier ("reminder", "sync_error", "info", ...).
    kind = Column(String(32), nullable=False, default="info")
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    # Optional opaque link target (e.g. "/calendar?event=<uuid>").
    link_url = Column(String(500), nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=dt.datetime.utcnow, index=True
    )
    read_at = Column(DateTime, nullable=True)
