"""Audit Log model — tracks all significant user/admin actions."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Who performed the action (nullable — some events are system-level)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Examples: LOGIN, LOGOUT, CREATE_USER, DELETE_USER, CHAT, CREATE_TRIP,
    #           UPLOAD_DOCUMENT, DELETE_DOCUMENT, ADMIN_ACTION

    resource: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Examples: "user", "trip", "chat_session", "rag_document"

    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    # "success" | "failure"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationship — optional, don't cascade (keep logs even if user deleted)
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} user_id={self.user_id}>"