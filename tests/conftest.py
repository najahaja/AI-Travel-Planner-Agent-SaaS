"""Shared pytest fixtures for all test files."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole

TEST_DB_URL = "sqlite+aiosqlite:///./test_conftest.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function", autouse=False)
async def db_setup():
    """Create fresh tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db_setup):
    """Get a test DB session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_setup):
    """AsyncClient with the test DB injected."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def super_admin_token(client: AsyncClient, db_session: AsyncSession):
    """Seed super admin and return its JWT token."""
    admin = User(
        email="superadmin@test.com",
        full_name="Super Admin",
        password_hash=hash_password("Test@Admin123!"),
        role=UserRole.SUPER_ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    resp = await client.post(
        "/auth/login",
        json={"email": "superadmin@test.com", "password": "Test@Admin123!"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, db_session: AsyncSession, super_admin_token: str):
    """Create an admin via super admin and return its JWT token."""
    await client.post(
        "/superadmin/admins",
        json={
            "email": "admin@test.com",
            "full_name": "Test Admin",
            "password": "Admin@Test123!",
        },
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "Admin@Test123!"},
    )
    return resp.json()["access_token"]
