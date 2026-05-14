"""Auth routes — login, refresh, logout with full audit logging."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user,
)
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, TokenResponse, UserResponse, RefreshRequest
from app.services.audit import log_action, AuditActions
# pyrefly: ignore [missing-import]
from loguru import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Failed login — wrong credentials
    if not user or not verify_password(payload.password, user.password_hash):
        # Log failure without user_id (we may not know who it is)
        await log_action(
            db=db, action=AuditActions.LOGIN_FAILED,
            user_id=user.id if user else None,
            detail=f"Failed login attempt for {payload.email}",
            ip_address=ip, user_agent=ua, status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        await log_action(
            db=db, action=AuditActions.LOGIN_FAILED,
            user_id=user.id, detail="Login attempt on deactivated account",
            ip_address=ip, user_agent=ua, status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact your administrator.",
        )

    token_data = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    await log_action(
        db=db, action=AuditActions.LOGIN,
        user_id=user.id, detail=f"Login: {user.role.value}",
        ip_address=ip, user_agent=ua,
    )
    await db.commit()
    logger.info(f"User logged in: {user.email} ({user.role})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Use refresh token to get new access token."""
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = int(token_data["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    await log_action(
        db=db, action=AuditActions.TOKEN_REFRESH,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    new_token_data = {"sub": str(user.id), "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(new_token_data),
        refresh_token=create_refresh_token(new_token_data),
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get currently authenticated user profile."""
    return UserResponse.model_validate(current_user)
