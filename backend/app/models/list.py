from __future__ import annotations
from typing import Optional

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ListCategory(str, enum.Enum):
    grocery = "grocery"
    todo = "todo"
    packing = "packing"
    school = "school"
    errands = "errands"
    custom = "custom"


class TaskList(Base):
    __tablename__ = "task_lists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("households.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[ListCategory] = mapped_column(
        default=ListCategory.custom, nullable=False
    )
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    household: Mapped["Household"] = relationship(foreign_keys=[household_id])  # noqa: F821
    items: Mapped[list["ListItem"]] = relationship(
        back_populates="task_list", cascade="all, delete-orphan", order_by="ListItem.sort_order"
    )

    def __repr__(self) -> str:
        return f"<TaskList id={self.id} name={self.name!r} category={self.category.value}>"


class ListItem(Base):
    __tablename__ = "list_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    is_checked: Mapped[bool] = mapped_column(default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False)
    assigned_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    task_list: Mapped["TaskList"] = relationship(back_populates="items")
    assigned_profile: Mapped[Optional["Profile"]] = relationship(  # noqa: F821
        foreign_keys=[assigned_profile_id]
    )

    def __repr__(self) -> str:
        return f"<ListItem id={self.id} text={self.text!r} checked={self.is_checked}>"
