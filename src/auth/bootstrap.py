from sqlalchemy import select
import asyncio
from src.auth.models import User,UserRole
from src.core.database import AsyncSessionLocal
from src.core.config import settings
from src.auth.security import hash_password


async def create_admin():
    async with AsyncSessionLocal() as db:
        try:
            existing_admin = (await db.execute(
                select(User).where(User.email == settings.ADMIN_EMAIL)
            )).scalar_one_or_none()

            if existing_admin:
                return

            admin_user = User(
                name=settings.ADMIN_NAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True
            )

            db.add(admin_user)
            await db.commit()

        except Exception as e:
            await db.rollback()
            raise e


if __name__=="__main__":
    asyncio.run(create_admin())