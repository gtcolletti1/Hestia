from __future__ import annotations
from typing import Optional

import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProfileRole(str, enum.Enum):
    admin = "admin"
    standard = "standard"
    kid = "kid"


class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    profiles: Mapped[list["Profile"]] = relationship(
        back_populates="household", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Household id={self.id} name={self.name!r}>"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, comment="Hex color, e.g. #FF5733")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    role: Mapped[ProfileRole] = mapped_column(
        default=ProfileRole.standard, nullable=False
    )
    pin_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    household: Mapped["Household"] = relationship(back_populates="profiles")

    def __repr__(self) -> str:
        return f"<Profile id={self.id} name={self.name!r} role={self.role.value}>"
