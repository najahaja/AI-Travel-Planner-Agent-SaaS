from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from fastapi import HTTPException
from app.core.config import settings
from loguru import logger


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,          # Never echo SQL in production-like mode
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency: yields an async DB session.

    NOTE: Routes are responsible for calling db.commit() themselves.
    This dependency only handles rollback on genuine DB/unexpected errors.
    HTTPException is re-raised cleanly without rollback or logging as a DB error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except HTTPException:
            # HTTPExceptions are business-logic errors, NOT database errors.
            # Re-raise them directly so FastAPI handles them correctly.
            raise
        except Exception as e:
            await session.rollback()
            logger.error(f"DB session error (rolled back): {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    from app.models import user, chat, travel, audit_log  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] Database tables initialized.")
