from typing import Optional

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealPlan(Base):
    __tablename__ = "meal_plans"

    __table_args__ = (
        UniqueConstraint(
            "household_id", "date", "meal_type",
            name="uq_meal_plan_per_type_per_day",
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
    meal_type: Mapped[MealType] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recipe_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    assigned_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        comment="Who is cooking",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    household: Mapped["Household"] = relationship(foreign_keys=[household_id])  # noqa: F821
    assigned_profile: Mapped[Optional["Profile"]] = relationship(  # noqa: F821
        foreign_keys=[assigned_profile_id]
    )

    def __repr__(self) -> str:
        return (
            f"<MealPlan id={self.id} date={self.date} "
            f"meal_type={self.meal_type.value} title={self.title!r}>"
        )
