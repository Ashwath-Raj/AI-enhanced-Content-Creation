from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_async_db_session
from src.users.schemas import UserCreate, UserRead, UserLogin
from src.users.crud import get_user_by_username, create_user
from src.auth import verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def register(user: UserCreate, db: AsyncSession = Depends(get_async_db_session)):
    existing = await get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    db_user = await create_user(db, user)
    return db_user


@router.post("/login")
async def login(form_data: UserLogin, db: AsyncSession = Depends(get_async_db_session)):
    user = await get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    access_token = create_access_token({"sub": str(user.id), "username": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
