from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException,status
from src.auth.models import User, UserRole
from src.auth.security import hash_password, verify_password


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )

    return result.scalar_one_or_none()


async def register_student(
    db: AsyncSession,
    name: str,
    email: str,
    password: str,
) -> User:

    existing_user = await get_user_by_email(
        db=db,
        email=email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.STUDENT,
    )

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:

    user = await get_user_by_email(
        db=db,
        email=email,
    )

    if user is None:
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    if not user.is_active:
        return None

    return user