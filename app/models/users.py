from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Role, TimestampMixin
from app.db.session import Base

if TYPE_CHECKING:
    from app.models.geography import PollingTable, School


class User(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    dni: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignment"
    __table_args__ = (
        UniqueConstraint("user_id", "table_id", "school_id", name="uq_assignment_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    table_id: Mapped[int | None] = mapped_column(
        ForeignKey("polling_table.id", ondelete="CASCADE"), nullable=True
    )
    school_id: Mapped[int | None] = mapped_column(
        ForeignKey("school.id", ondelete="CASCADE"), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="assignments")
    table: Mapped["PollingTable"] = relationship(back_populates="assignments")
    school: Mapped["School"] = relationship()
