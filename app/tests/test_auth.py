import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from app.schemas.auth import UserCreate, UserLogin

@pytest_asyncio.fixture
def auth_headers(test_user):
    return {"Authorization": "Bearer testtoken"}

@pytest.mark.asyncio
def test_register_user(client: TestClient, override_get_db):
    user_data = UserCreate(username="newuser", email="new@example.com", password="password123")
    response = client.post("/auth/register", json=user_data.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert "access_token" in data

@pytest.mark.asyncio
def test_register_duplicate_user(client: TestClient, override_get_db, test_user):
    user_data = UserCreate(username="testuser", email="new@example.com", password="password123")
    response = client.post("/auth/register", json=user_data.dict())
    assert response.status_code == 400
    assert response.json()["detail"] == "Username exists"

@pytest.mark.asyncio
def test_login_user(client: TestClient, override_get_db, test_user, monkeypatch):
    async def mock_verify_password(plain, hashed):
        return True
    monkeypatch.setattr("app.services.auth.verify_password", mock_verify_password)

    login_data = UserLogin(username="testuser", password="password123")
    response = client.post("/auth/login", json=login_data.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "access_token" in data

@pytest.mark.asyncio
def test_login_invalid_credentials(client: TestClient, override_get_db, test_user, monkeypatch):
    async def mock_verify_password(plain, hashed):
        return False
    monkeypatch.setattr("app.services.auth.verify_password", mock_verify_password)

    login_data = UserLogin(username="testuser", password="wrongpassword")
    response = client.post("/auth/login", json=login_data.dict())
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid credentials"