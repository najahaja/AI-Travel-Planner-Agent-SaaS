"""Reports & Audit Logs routes — admin and super admin visibility."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import require_admin_or_above, require_super_admin
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole

router = APIRouter(prefix="/reports", tags=["Reports & Audit Logs"])


# ── Schemas ───────────────────────────────────────────────────────────────────
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource: Optional[str]
    resource_id: Optional[int]
    detail: Optional[str]
    ip_address: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogList(BaseModel):
    total: int
    logs: list[AuditLogResponse]


class UsageStats(BaseModel):
    period: str
    total_chats: int
    total_trips_created: int
    total_logins: int
    total_failed_logins: int
    total_pdf_exports: int
    unique_active_users: int


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/audit-logs", response_model=AuditLogList)
async def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by status: success|failure"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """
    Get audit logs.
    - Super admin sees all logs.
    - Admin sees only logs for their own users.
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if action:
        query = query.where(AuditLog.action == action.upper())
    if status:
        query = query.where(AuditLog.status == status)

    # Admin isolation — restrict to their users only
    if current_admin.role == UserRole.ADMIN:
        their_user_ids_q = select(User.id).where(User.admin_id == current_admin.id)
        query = query.where(AuditLog.user_id.in_(their_user_ids_q))
    elif user_id:
        query = query.where(AuditLog.user_id == user_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_q) or 0

    result = await db.execute(query.offset(offset).limit(limit))
    logs = result.scalars().all()

    return AuditLogList(
        total=total,
        logs=[AuditLogResponse.model_validate(log) for log in logs],
    )


@router.get("/usage-stats", response_model=UsageStats)
async def get_usage_stats(
    days: int = Query(7, ge=1, le=90, description="Period in days"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """System usage statistics for the given period."""
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=days)

    base = select(func.count(AuditLog.id)).where(AuditLog.created_at >= since)

    # Admin isolation
    if current_admin.role == UserRole.ADMIN:
        their_ids = select(User.id).where(User.admin_id == current_admin.id)
        base = base.where(AuditLog.user_id.in_(their_ids))

    async def count_action(action: str) -> int:
        return await db.scalar(base.where(AuditLog.action == action)) or 0

    total_chats = await count_action("CHAT")
    total_trips = await count_action("CREATE_TRIP")
    total_logins = await count_action("LOGIN")
    total_failed = await count_action("LOGIN_FAILED")
    total_pdfs = await count_action("EXPORT_PDF")

    # Unique active users
    unique_q = select(func.count(AuditLog.user_id.distinct())).where(
        AuditLog.created_at >= since,
        AuditLog.user_id.isnot(None),
    )
    if current_admin.role == UserRole.ADMIN:
        their_ids2 = select(User.id).where(User.admin_id == current_admin.id)
        unique_q = unique_q.where(AuditLog.user_id.in_(their_ids2))

    unique_users = await db.scalar(unique_q) or 0

    return UsageStats(
        period=f"Last {days} days",
        total_chats=total_chats,
        total_trips_created=total_trips,
        total_logins=total_logins,
        total_failed_logins=total_failed,
        total_pdf_exports=total_pdfs,
        unique_active_users=unique_users,
    )
