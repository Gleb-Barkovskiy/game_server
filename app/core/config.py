from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://testuser:testpassword@localhost:5432/testdb"

    REDIS_URL: str = "redis://localhost:6379/0"

    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None

    USE_REDIS_REST_API: bool = False

    JWT_SECRET_KEY: str = "testsecret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    LOCATION_LIST: List[str] = [
        "Paris", "Tokyo Airport", "London Museum",
        "New York Subway", "Rome Colosseum", "Sydney Opera House"
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def __init__(self, **data):
        super().__init__(**data)
        if self.UPSTASH_REDIS_REST_URL and self.UPSTASH_REDIS_REST_TOKEN:
            self.USE_REDIS_REST_API = True


@lru_cache()
def get_settings():
    return Settings()