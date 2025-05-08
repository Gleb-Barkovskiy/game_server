import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from async_asgi_testclient import TestClient as WebSocketTestClient
from app.services.auth import create_access_token

@pytest_asyncio.fixture
def auth_headers():
    token = create_access_token(data={"sub": "testuser"})
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
def test_join_pool_new_user(client: TestClient, auth_headers, mock_redis):
    mock_redis.get.return_value = None
    mock_redis.sadd.return_value = True
    response = client.post("/game/join-pool", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Added to waiting pool"}

@pytest.mark.asyncio
def test_join_pool_existing_room(client: TestClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    response = client.post("/game/join-pool", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Already assigned to a room", "room_id": "room123"}

@pytest.mark.asyncio
def test_get_pending_room(client: TestClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    response = client.get("/game/pending-room", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"room_id": "room123"}

@pytest.mark.asyncio
def test_get_pending_room_none(client: TestClient, auth_headers, mock_redis):
    mock_redis.get.return_value = None
    response = client.get("/game/pending-room", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "No room assigned yet"

@pytest.mark.asyncio
async def test_room_websocket_connect(monkeypatch):
    from app.main import app
    client = WebSocketTestClient(app)
    token = create_access_token(data={"sub": "testuser"})
    monkeypatch.setattr("app.redis.redis_client.get", AsyncMock(return_value=b"room123"))
    monkeypatch.setattr("app.redis.redis_client.hgetall", AsyncMock(return_value={
        b"users": b"testuser,user2",
        b"spy": b"testuser",
        b"secret_location": b"location1",
        b"status": b"active",
        b"current_turn": b"0",
        b"questions": b"[]"
    }))
    monkeypatch.setattr("app.redis.redis_client.sadd", AsyncMock())
    monkeypatch.setattr("app.redis.redis_client.scard", AsyncMock(return_value=2))
    monkeypatch.setattr("app.redis.redis_client.hget", AsyncMock(return_value=None))
    monkeypatch.setattr("app.redis.redis_client.hset", AsyncMock())
    async with client.websocket_connect(f"/game/ws/room123?token={token}") as websocket:
        message = await websocket.receive_json()
        assert message == {"type": "role", "role": "spy", "locations": ["Paris", "Tokyo Airport", "London Museum", "New York Subway", "Rome Colosseum", "Sydney Opera House"]}