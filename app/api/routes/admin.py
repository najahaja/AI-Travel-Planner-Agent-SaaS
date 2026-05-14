"""Admin routes — manage own users only."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.security import require_admin_or_above, hash_password
from app.models.user import User, UserRole
from app.models.travel import TravelPlan
from app.schemas.user import UserCreate, UserResponse, UserListResponse, UserUpdate
from app.schemas.travel import TravelPlanListResponse, TravelPlanResponse
# pyrefly: ignore [missing-import]
from loguru import logger

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=UserListResponse)
async def list_my_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """List users belonging to this admin only."""
    # Super admin can see all users; regular admin sees only their own
    if current_admin.role == UserRole.SUPER_ADMIN:
        result = await db.execute(
            select(User).where(User.role == UserRole.USER).order_by(User.created_at.desc())
        )
    else:
        result = await db.execute(
            select(User).where(
                and_(User.admin_id == current_admin.id, User.role == UserRole.USER)
            ).order_by(User.created_at.desc())
        )
    users = result.scalars().all()
    return UserListResponse(total=len(users), users=[UserResponse.model_validate(u) for u in users])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """Create a new user under this admin."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Admins can only create users; super admins can create either
    target_role = UserRole.USER
    if current_admin.role == UserRole.SUPER_ADMIN and payload.role == UserRole.ADMIN:
        target_role = UserRole.ADMIN

    # Determine admin_id
    assigned_admin_id = None
    if current_admin.role == UserRole.SUPER_ADMIN:
        assigned_admin_id = payload.admin_id
    elif current_admin.role == UserRole.ADMIN:
        assigned_admin_id = current_admin.id

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=target_role,
        admin_id=assigned_admin_id,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    logger.info(f"Admin {current_admin.email} created user: {user.email}")
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """Get specific user — admin can only access their own users."""
    user = await _get_user_for_admin(user_id, current_admin, db)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """Update user details — admin restricted to their own users."""
    user = await _get_user_for_admin(user_id, current_admin, db)

    if payload.full_name:
        user.full_name = payload.full_name
    if payload.email:
        user.email = payload.email
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.admin_id is not None and current_admin.role == UserRole.SUPER_ADMIN:
        user.admin_id = payload.admin_id

    await db.flush()
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """Delete user — admin restricted to their own users."""
    user = await _get_user_for_admin(user_id, current_admin, db)
    await db.delete(user)
    await db.commit()
    logger.info(f"Admin {current_admin.email} deleted user: {user.email}")


@router.get("/users/{user_id}/trips", response_model=TravelPlanListResponse)
async def get_user_trips(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_or_above),
):
    """View travel plans for a user under this admin."""
    await _get_user_for_admin(user_id, current_admin, db)  # Access check

    result = await db.execute(
        select(TravelPlan)
        .where(TravelPlan.user_id == user_id)
        .order_by(TravelPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return TravelPlanListResponse(
        total=len(plans),
        plans=[TravelPlanResponse.model_validate(p) for p in plans],
    )


# ── Helper ─────────────────────────────────────────────────────────────────────
async def _get_user_for_admin(user_id: int, admin: User, db: AsyncSession) -> User:
    """Get user if admin has access; raise 404 otherwise (prevents info leakage)."""
    if admin.role == UserRole.SUPER_ADMIN:
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.role == UserRole.USER))
        )
    else:
        result = await db.execute(
            select(User).where(
                and_(
                    User.id == user_id,
                    User.admin_id == admin.id,
                    User.role == UserRole.USER,
                )
            )
        )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
