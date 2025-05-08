from fastapi import APIRouter, Depends, HTTPException
from app.schemas.auth import UserCreate, Token, UserLogin, LoginResponse
from app.models.user import User
from app.services.auth import hash_password, create_access_token, verify_password
from app.database import async_session
from sqlalchemy.future import select

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == user.username))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Username exists")
        hashed = hash_password(user.password)
        db_user = User(username=user.username, email=user.email, hashed_password=hashed)
        session.add(db_user)
        await session.commit()
        token = create_access_token(data={"sub": user.username})
        return {"access_token": token, "token_type": "bearer", "username": user.username}

@router.post("/login", response_model=LoginResponse)
async def login(user: UserLogin):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == user.username))
        db_user = result.scalars().first()
        if not db_user or not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid credentials")
        token = create_access_token(data={"sub": db_user.username})
        print(db_user.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": db_user.username,
        }