from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_async_db_session
from src.users.schemas import UserCreate, UserRead, UserUpdate
from src.users.crud import get_user, create_user, update_user, delete_user
from src.auth_dependency import get_current_user

router = APIRouter()


@router.post("/users", response_model=UserRead)
async def create_user_route(
    user: UserCreate, db: AsyncSession = Depends(get_async_db_session)
):
    db_user = await create_user(db, user)
    return db_user


@router.get("/users/{user_id}", response_model=UserRead)
async def read_user(user_id: int, db: AsyncSession = Depends(get_async_db_session)):
    db_user = await get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/users/{user_id}", response_model=UserRead)
async def update_user_route(
    user_id: int, user: UserUpdate, db: AsyncSession = Depends(get_async_db_session)
):
    db_user = await update_user(db, user_id, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}")
async def delete_user_route(
    user_id: int, db: AsyncSession = Depends(get_async_db_session)
):
    db_user = await delete_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@router.get("/users/me", response_model=UserRead)
async def read_current_user(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    user = await get_user(db, int(current_user["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
