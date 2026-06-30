import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.user,
    ) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password, role=role)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user
