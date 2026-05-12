"""Audit log service — write audit entries to the database."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from loguru import logger


class AuditActions:
    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOKEN_REFRESH = "TOKEN_REFRESH"

    # User management
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DELETE_USER = "DELETE_USER"
    DEACTIVATE_USER = "DEACTIVATE_USER"

    # Admin management
    CREATE_ADMIN = "CREATE_ADMIN"
    UPDATE_ADMIN = "UPDATE_ADMIN"
    DELETE_ADMIN = "DELETE_ADMIN"

    # AI / Agent
    CHAT = "CHAT"
    CREATE_TRIP = "CREATE_TRIP"
    DELETE_SESSION = "DELETE_SESSION"

    # RAG
    UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
    DELETE_DOCUMENT = "DELETE_DOCUMENT"

    # Exports
    EXPORT_PDF = "EXPORT_PDF"


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    resource: Optional[str] = None,
    resource_id: Optional[int] = None,
    detail: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    status: str = "success",
    extra: Optional[dict] = None,
) -> None:
    """Write an audit log entry. Never raises — audit failures must not break requests."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            extra=extra,
        )
        db.add(entry)
        # Don't commit here — the route's DB session will commit
    except Exception as e:
        logger.warning(f"[AUDIT] Failed to write audit log: {e}")
