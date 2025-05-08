import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.services.auth import create_access_token

@pytest_asyncio.fixture
async def auth_headers():
    token = create_access_token(data={"sub": "testuser"})
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_room_info(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    mock_redis.hgetall.return_value = {
        b"status": b"active",
        b"users": b"testuser,user2"
    }
    response = await client.get("/room/room123", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {
        "room_id": "room123",
        "status": "active",
        "users": ["testuser", "user2"]
    }

@pytest.mark.asyncio
async def test_get_room_info_unauthorized(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room456"
    response = await client.get("/room/room123", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized for this room"

@pytest.mark.asyncio
async def test_get_room_users(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    mock_redis.hgetall.return_value = {b"users": b"testuser,user2"}
    response = await client.get("/room/room123/users", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"users": ["testuser", "user2"]}

@pytest.mark.asyncio
async def test_leave_room(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    mock_redis.hgetall.return_value = {
        b"users": b"testuser,user2",
        b"current_turn": b"0"
    }
    mock_redis.delete.return_value = 1
    mock_redis.hset.return_value = None
    mock_redis.publish.return_value = None
    response = await client.post("/room/room123/leave", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Left room successfully"}