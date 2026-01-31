from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.users import User
from src.users.schemas import UserCreate, UserUpdate
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from src.auth import get_password_hash, verify_password


async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar()


async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar()


async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    db.add(db_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, user_id: int, user: UserUpdate):
    db_user = await get_user(db, user_id)
    if db_user is None:
        return None
    if user.username:
        db_user.username = user.username
    if user.email:
        db_user.email = user.email
    if user.password:
        db_user.hashed_password = get_password_hash(user.password)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int):
    db_user = await get_user(db, user_id)
    if db_user is None:
        return None
    await db.delete(db_user)
    await db.commit()
    return db_user
