import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock
from async_asgi_testclient import TestClient
from app.services.auth import create_access_token
from app.services.game import add_user_to_pool, find_match, start_turn, process_votes

@pytest_asyncio.fixture
async def auth_headers():
    token = create_access_token(data={"sub": "testuser"})
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_join_pool_new_user(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = None
    mock_redis.sadd.return_value = True
    response = await client.post("/game/join-pool", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Added to waiting pool"}

@pytest.mark.asyncio
async def test_join_pool_existing_room(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    response = await client.post("/game/join-pool", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"message": "Already assigned to a room", "room_id": "room123"}

@pytest.mark.asyncio
async def test_get_pending_room(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = b"room123"
    response = await client.get("/game/pending-room", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"room_id": "room123"}

@pytest.mark.asyncio
async def test_get_pending_room_none(client: AsyncClient, auth_headers, mock_redis):
    mock_redis.get.return_value = None
    response = await client.get("/game/pending-room", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "No room assigned yet"

@pytest.mark.asyncio
async def test_room_websocket_connect(monkeypatch):
    from app.main import app
    client = TestClient(app)
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
        assert message == {"type": "role", "role": "spy", "locations": ["location1", "location2"]}

@pytest.mark.asyncio
async def test_add_user_to_pool_new(mock_redis):
    mock_redis.get.return_value = None
    mock_redis.sadd.return_value = True
    result = await add_user_to_pool("testuser")
    assert result is True

@pytest.mark.asyncio
async def test_add_user_to_pool_existing_room(mock_redis):
    mock_redis.get.return_value = b"room123"
    result = await add_user_to_pool("testuser")
    assert result is False

@pytest.mark.asyncio
async def test_find_match(mock_redis, monkeypatch):
    mock_redis.scard.return_value = 3
    mock_redis.srandmember.return_value = [b"testuser", b"user2", b"user3"]
    monkeypatch.setattr("app.services.game_service.random.choice", lambda x: x[0])
    await find_match()
    mock_redis.hset.assert_called()
    mock_redis.publish.assert_called()

@pytest.mark.asyncio
async def test_start_turn_active(mock_redis):
    mock_redis.hgetall.return_value = {
        b"status": b"active",
        b"users": b"testuser,user2",
        b"questions": b"[]"
    }
    mock_redis.publish.return_value = None
    await start_turn("room123", 0)
    mock_redis.publish.assert_called()

@pytest.mark.asyncio
async def test_process_votes_spy_win(mock_redis):
    mock_redis.hgetall.return_value = {
        b"votes": b'{"testuser": "spyuser", "user2": "spyuser"}',
        b"users": b"testuser,user2,spyuser",
        b"spy": b"spyuser"
    }
    mock_redis.hset.return_value = None
    mock_redis.publish.return_value = None
    await process_votes("room123")
    mock_redis.publish.assert_called_with(
        "room_channel:room123",
        '{"type": "players_win", "spy": "spyuser"}'
    )

@pytest.mark.asyncio
async def test_process_votes_tie(mock_redis):
    mock_redis.hgetall.return_value = {
        b"votes": b'{"testuser": "user2", "user2": "testuser"}',
        b"users": b"testuser,user2",
        b"spy": b"testuser"
    }
    mock_redis.hset.return_value = None
    mock_redis.publish.return_value = None
    await process_votes("room123")
    mock_redis.publish.assert_called_with(
        "room_channel:room123",
        '{"type": "voting_tie"}'
    )