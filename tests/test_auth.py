import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.schemas.auth import UserCreate, UserLogin


@pytest_asyncio.fixture
async def auth_headers(test_user):
    return {"Authorization": "Bearer testtoken"}

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, override_get_db):
    user_data = UserCreate(username="newuser", email="new@example.com", password="password123")
    response = await client.post("/auth/register", json=user_data.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert "access_token" in data

@pytest.mark.asyncio
async def test_register_duplicate_user(client: AsyncClient, override_get_db, test_user):
    user_data = UserCreate(username="testuser", email="new@example.com", password="password123")
    response = await client.post("/auth/register", json=user_data.dict())
    assert response.status_code == 400
    assert response.json()["detail"] == "Username exists"

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, override_get_db, test_user, monkeypatch):
    async def mock_verify_password(plain, hashed):
        return True
    monkeypatch.setattr("app.services.auth.verify_password", mock_verify_password)

    login_data = UserLogin(username="testuser", password="password123")
    response = await client.post("/auth/login", json=login_data.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "access_token" in data

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, override_get_db, test_user, monkeypatch):
    async def mock_verify_password(plain, hashed):
        return False
    monkeypatch.setattr("app.services.auth.verify_password", mock_verify_password)

    login_data = UserLogin(username="testuser", password="wrongpassword")
    response = await client.post("/auth/login", json=login_data.dict())
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid credentials"