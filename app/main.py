"""
AI Travel Planner Agent — FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api.routes import auth, admin, superadmin, agent, reports, export


# ── Rate Limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    setup_logging()
    logger.info("[STARTUP] Starting AI Travel Planner Agent...")

    # Create log directory
    os.makedirs("logs", exist_ok=True)

    # Initialize database tables
    await init_db()

    # Seed super admin if not exists
    await seed_super_admin()

    logger.info(f"[OK] Application ready - {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("[DOCS] API Docs: http://localhost:8000/docs")

    yield

    logger.info("[SHUTDOWN] Shutting down...")


# ── App Instance ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## 🌍 AI Travel Planner Agent API

A professional AI-powered travel planning system with:
- **LangGraph Agent** — Stateful multi-step AI reasoning
- **RAG** — Retrieval-Augmented Generation from travel knowledge base
- **RBAC** — Role-based access: Super Admin → Admin → User
- **Real-time tools** — Weather, budget estimation, itinerary planning

### Roles
| Role | Access |
|------|--------|
| `super_admin` | Full system access, manages all admins |
| `admin` | Manages their own users |
| `user` | Uses the travel planner agent |

### Quick Start
1. Login at `/auth/login` to get a JWT token
2. Use the token as `Bearer <token>` in the Authorization header
3. Chat with the agent at `/agent/chat`
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."},
    )


# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(superadmin.router)
app.include_router(admin.router)
app.include_router(agent.router)
app.include_router(reports.router)
app.include_router(export.router)


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"])
async def root():
    """Welcome endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "features": ["AI Agent", "RAG", "RBAC", "Audit Logs", "PDF Export"],
    }


# ── Super Admin Seeder ────────────────────────────────────────────────────────
async def seed_super_admin():
    """Create the default super admin if not present."""
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.role == UserRole.SUPER_ADMIN)
        )
        if result.scalar_one_or_none():
            return  # Already exists

        super_admin = User(
            email=settings.SUPER_ADMIN_EMAIL,
            full_name="Super Administrator",
            password_hash=hash_password(settings.SUPER_ADMIN_PASSWORD),
            role=UserRole.SUPER_ADMIN,
        )
        db.add(super_admin)
        await db.commit()
        logger.info(f"[SEED] Super admin created: {settings.SUPER_ADMIN_EMAIL}")
