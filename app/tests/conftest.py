from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.main import app
from app.redis import redis_client

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture
async def mock_redis():
    mock = AsyncMock()
    redis_client.hgetall = mock.hgetall
    redis_client.get = mock.get
    redis_client.setex = mock.setex
    redis_client.sadd = mock.sadd
    redis_client.srem = mock.srem
    redis_client.scard = mock.scard
    redis_client.srandmember = mock.srandmember
    redis_client.hset = mock.hset
    redis_client.exists = mock.exists
    redis_client.delete = mock.delete
    redis_client.publish = mock.publish
    redis_client.expire = mock.expire

    # Mock pubsub
    pubsub_mock = AsyncMock()
    pubsub_mock.subscribe = AsyncMock()
    pubsub_mock.listen = AsyncMock(return_value=[{"type": "message", "data": b'{"type": "test"}'}])
    pubsub_mock.unsubscribe = AsyncMock()
    redis_client.pubsub = MagicMock(return_value=pubsub_mock)

    yield mock

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def override_get_db(db_session):
    async def _get_db():
        yield db_session
    app.dependency_overrides[app.get_db] = _get_db
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def test_user(db_session):
    from app.models.user import User
    user = User(username="testuser", email="test@example.com", hashed_password="hashedpassword")
    db_session.add(user)
    await db_session.commit()
    yield user