from typing import Optional

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OAuthProvider(str, enum.Enum):
    google = "google"
    microsoft = "microsoft"
    todoist = "todoist"


class SyncAction(str, enum.Enum):
    create = "create"
    update = "update"
    delete = "delete"


class SyncStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[OAuthProvider] = mapped_column(nullable=False)
    access_token: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Encrypted at rest — use app-level encryption"
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    account_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    household: Mapped["Household"] = relationship(foreign_keys=[household_id])  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<OAuthCredential id={self.id} provider={self.provider.value} "
            f"email={self.account_email!r}>"
        )


class SyncQueueItem(Base):
    __tablename__ = "sync_queue_items"

    __table_args__ = (
        Index("ix_sync_queue_processing", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. 'event', 'list_item'"
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[SyncAction] = mapped_column(nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[SyncStatus] = mapped_column(
        default=SyncStatus.pending, nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    household: Mapped["Household"] = relationship(foreign_keys=[household_id])  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<SyncQueueItem id={self.id} entity={self.entity_type}:{self.entity_id} "
            f"action={self.action.value} status={self.status.value}>"
        )
