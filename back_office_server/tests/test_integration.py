"""
Integration tests for Back Office Server
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.config.database import Base, get_db
from app.config.settings import settings


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield TestSessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test basic health endpoints"""

    @pytest.mark.asyncio
    async def test_root(self, client):
        """Test root endpoint"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health(self, client):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestUserEndpoints:
    """Test user management endpoints"""

    @pytest.mark.asyncio
    async def test_create_user(self, client):
        """Test user creation"""
        user_data = {
            "email": "test@example.com",
            "password": "TestPass123",
            "broker_id": "test_broker",
            "name": "Test User"
        }

        response = await client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["broker_id"] == user_data["broker_id"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_users(self, client):
        """Test listing users"""
        # Create a user first
        user_data = {
            "email": "test2@example.com",
            "password": "TestPass123",
            "broker_id": "test_broker"
        }
        await client.post("/api/v1/users/", json=user_data)

        # List users
        response = await client.get("/api/v1/users/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_get_user(self, client):
        """Test getting user by ID"""
        # Create a user
        user_data = {
            "email": "test3@example.com",
            "password": "TestPass123",
            "broker_id": "test_broker"
        }
        create_response = await client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]

        # Get user
        response = await client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == user_data["email"]

    @pytest.mark.asyncio
    async def test_update_user(self, client):
        """Test updating user"""
        # Create a user
        user_data = {
            "email": "test4@example.com",
            "password": "TestPass123",
            "broker_id": "test_broker"
        }
        create_response = await client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]

        # Update user
        update_data = {"name": "Updated Name"}
        response = await client.put(f"/api/v1/users/{user_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_user(self, client):
        """Test deleting user"""
        # Create a user
        user_data = {
            "email": "test5@example.com",
            "password": "TestPass123",
            "broker_id": "test_broker"
        }
        create_response = await client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]

        # Delete user
        response = await client.delete(f"/api/v1/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deletion
        get_response = await client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 404


class TestSessionEndpoints:
    """Test session management endpoints"""

    @pytest.mark.asyncio
    async def test_get_sessions(self, client):
        """Test getting active sessions"""
        response = await client.get("/api/v1/sessions/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "sessions" in data


class TestDashboardEndpoints:
    """Test dashboard endpoints"""

    @pytest.mark.asyncio
    async def test_dashboard_overview(self, client):
        """Test dashboard overview"""
        response = await client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "active_sessions" in data
        assert "total_balance" in data

    @pytest.mark.asyncio
    async def test_performance_metrics(self, client):
        """Test performance metrics"""
        response = await client.get("/api/v1/dashboard/performance?period=7d")
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "total_trades" in data
        assert "win_rate" in data


class TestTradingEndpoints:
    """Test trading endpoints"""

    @pytest.mark.asyncio
    async def test_get_positions(self, client):
        """Test getting positions"""
        response = await client.get("/api/v1/trading/positions")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "positions" in data

    @pytest.mark.asyncio
    async def test_get_orders(self, client):
        """Test getting orders"""
        response = await client.get("/api/v1/trading/orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_get_trades(self, client):
        """Test getting trades"""
        response = await client.get("/api/v1/trading/trades")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
