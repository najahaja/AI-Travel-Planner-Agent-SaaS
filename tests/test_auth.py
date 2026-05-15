"""Tests for auth endpoints."""
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
# pyrefly: ignore [missing-import]
from app.main import app
# pyrefly: ignore [missing-import]
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole

# ── Test DB ────────────────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_travel.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


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


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test super admin
    async with TestSessionLocal() as db:
        admin = User(
            email="superadmin@test.com",
            full_name="Test Super Admin",
            password_hash=hash_password("Test@Admin123!"),
            role=UserRole.SUPER_ADMIN,
        )
        db.add(admin)
        await db.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health_check(client):
    async with client as c:
        response = await c.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_login_success(client):
    async with client as c:
        response = await c.post("/auth/login", json={
            "email": "superadmin@test.com",
            "password": "Test@Admin123!",
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["role"] == "super_admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    async with client as c:
        response = await c.post("/auth/login", json={
            "email": "superadmin@test.com",
            "password": "WrongPassword!",
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    async with client as c:
        response = await c.post("/auth/login", json={
            "email": "nobody@test.com",
            "password": "AnyPassword123!",
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client):
    async with client as c:
        # Login first
        login_resp = await c.post("/auth/login", json={
            "email": "superadmin@test.com",
            "password": "Test@Admin123!",
        })
        token = login_resp.json()["access_token"]

        # Get profile
        me_resp = await c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "superadmin@test.com"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    async with client as c:
        response = await c.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_super_admin_create_admin(client):
    async with client as c:
        # Login as super admin
        login_resp = await c.post("/auth/login", json={
            "email": "superadmin@test.com",
            "password": "Test@Admin123!",
        })
        token = login_resp.json()["access_token"]

        # Create admin
        create_resp = await c.post(
            "/superadmin/admins",
            json={
                "email": "newadmin@test.com",
                "full_name": "Test Admin",
                "password": "Admin@Test123!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["role"] == "admin"
    assert data["email"] == "newadmin@test.com"


@pytest.mark.asyncio
async def test_admin_cannot_access_superadmin_routes(client):
    async with client as c:
        # Login as super admin
        login_resp = await c.post("/auth/login", json={
            "email": "superadmin@test.com",
            "password": "Test@Admin123!",
        })
        token = login_resp.json()["access_token"]

        # Create admin
        await c.post(
            "/superadmin/admins",
            json={"email": "admin2@test.com", "full_name": "Admin 2", "password": "Admin@Test123!"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Login as admin
        admin_login = await c.post("/auth/login", json={
            "email": "admin2@test.com",
            "password": "Admin@Test123!",
        })
        admin_token = admin_login.json()["access_token"]

        # Try to access super admin route
        resp = await c.get(
            "/superadmin/admins",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 403
