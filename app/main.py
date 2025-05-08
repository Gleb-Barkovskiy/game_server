from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.game import router as game_router
from app.api.room import router as room_router
from app.database import init_db
from app.core.config import get_settings
import asyncio
from contextlib import asynccontextmanager

from app.services.game import find_match

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(matchmaking_loop())
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Set-Cookie",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Origin",
        "Authorization",
    ],
)

app.include_router(auth_router)
app.include_router(game_router)
app.include_router(room_router)

async def matchmaking_loop():
    while True:
        await asyncio.sleep(5)
        await find_match()
