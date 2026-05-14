"""Super Admin routes — manage all admins and their users."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.security import require_super_admin, hash_password
from app.models.user import User, UserRole
from app.models.chat import ChatSession
from app.models.travel import TravelPlan
from app.schemas.user import AdminCreate, UserResponse, UserListResponse, UserUpdate
from app.schemas.travel import SuperAdminAnalytics
# pyrefly: ignore [missing-import]
from loguru import logger

router = APIRouter(prefix="/superadmin", tags=["Super Admin"])


@router.get("/analytics", response_model=SuperAdminAnalytics)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Global system analytics — super admin only."""
    total_admins = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.ADMIN))
    total_users = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.USER))
    total_sessions = await db.scalar(select(func.count(ChatSession.id)))
    total_plans = await db.scalar(select(func.count(TravelPlan.id)))

    from datetime import datetime, timedelta, timezone
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_users = await db.scalar(
        select(func.count(ChatSession.user_id.distinct()))
        .where(ChatSession.created_at >= seven_days_ago)
    )

    return SuperAdminAnalytics(
        total_admins=total_admins or 0,
        total_users=total_users or 0,
        total_conversations=total_sessions or 0,
        total_travel_plans=total_plans or 0,
        active_users_last_7_days=active_users or 0,
    )


@router.get("/admins", response_model=UserListResponse)
async def list_all_admins(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """List all admin accounts."""
    result = await db.execute(
        select(User).where(User.role == UserRole.ADMIN).order_by(User.created_at.desc())
    )
    admins = result.scalars().all()
    return UserListResponse(total=len(admins), users=[UserResponse.model_validate(a) for a in admins])


@router.post("/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    payload: AdminCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Create a new admin account."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    admin = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    await db.flush()
    await db.commit()
    await db.refresh(admin)
    logger.info(f"Super admin created admin: {admin.email}")
    return UserResponse.model_validate(admin)


@router.get("/admins/{admin_id}", response_model=UserResponse)
async def get_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Get a specific admin's details."""
    result = await db.execute(
        select(User).where(and_(User.id == admin_id, User.role == UserRole.ADMIN))
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return UserResponse.model_validate(admin)


@router.patch("/admins/{admin_id}", response_model=UserResponse)
async def update_admin(
    admin_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Update admin account (activate/deactivate, update details)."""
    result = await db.execute(
        select(User).where(and_(User.id == admin_id, User.role == UserRole.ADMIN))
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if payload.full_name:
        admin.full_name = payload.full_name
    if payload.email:
        admin.email = payload.email
    if payload.is_active is not None:
        admin.is_active = payload.is_active
    if payload.password:
        admin.password_hash = hash_password(payload.password)

    await db.flush()
    await db.commit()
    await db.refresh(admin)
    return UserResponse.model_validate(admin)


@router.delete("/admins/{admin_id}", status_code=204)
async def delete_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Delete admin and optionally their users."""
    result = await db.execute(
        select(User).where(and_(User.id == admin_id, User.role == UserRole.ADMIN))
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.delete(admin)
    await db.commit()
    logger.info(f"Super admin deleted admin: {admin.email}")


@router.get("/admins/{admin_id}/users", response_model=UserListResponse)
async def get_admin_users(
    admin_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    """Get all users under a specific admin."""
    result = await db.execute(
        select(User).where(
            and_(User.admin_id == admin_id, User.role == UserRole.USER)
        ).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return UserListResponse(total=len(users), users=[UserResponse.model_validate(u) for u in users])
