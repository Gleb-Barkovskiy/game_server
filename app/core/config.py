import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://testuser:testpassword@localhost:5432/testdb"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "testsecret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    LOCATION_LIST: List[str] = [
        "Paris", "Tokyo Airport", "London Museum",
        "New York Subway", "Rome Colosseum", "Sydney Opera House"
    ]

    model_config = SettingsConfigDict(env_file="/.env", env_file_encoding="utf-8")


@lru_cache()
def get_settings():
    return Settings()