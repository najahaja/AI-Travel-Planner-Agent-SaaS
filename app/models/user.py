import enum
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Self-referential FK: user.admin_id → admin user
    # Super admins and admins have admin_id = None
    admin_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    # Admin → managed users (one admin has many users)
    managed_users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="admin",
        foreign_keys="[User.admin_id]",
    )
    admin: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="managed_users",
        remote_side="User.id",
        foreign_keys="[User.admin_id]",
    )

    # pyrefly: ignore [missing-import-error, unknown-type]
    chat_sessions: Mapped[List["ChatSession"]] = relationship(  # noqa: F821
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    # pyrefly: ignore [missing-import-error, unknown-type]
    travel_plans: Mapped[List["TravelPlan"]] = relationship(  # noqa: F821
        "TravelPlan", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
