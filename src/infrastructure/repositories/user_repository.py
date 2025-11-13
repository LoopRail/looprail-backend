from typing import Optional, Tuple
from uuid import UUID

from pydantic import EmailStr
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.repositories.base_repository import BaseRepository
from src.models.user_model import User, UserProfile, UserRepository
from src.types.error import Error, error


class SQLUserRepository(UserRepository, BaseRepository):
    """
    Concrete implementation of the user repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def create_user(self, *, user: User) -> Tuple[Optional[User], Error]:
        return await user.create(self.session)

    async def get_user_by_id(self, *, user_id: UUID) -> Tuple[Optional[User], Error]:
        user = await User.get(self.session, user_id)
        if not user:
            return None, error("User not found")
        return user, None

    async def get_user_by_username(self, *, username: str) -> Tuple[Optional[User], Error]:
        user = await User.find_one(self.session, username=username)
        if not user:
            return None, error("User not found")
        return user, None

    async def get_user_by_email(self, *, email: EmailStr) -> Tuple[Optional[User], Error]:
        user = await User.find_one(self.session, email=email)
        if not user:
            return None, error("User not found")
        return user, None

    async def list_users(self, *, limit: int = 50, offset: int = 0) -> Tuple[list[User], Error]:
        try:
            statement = select(User).offset(offset).limit(limit)
            result = await self.session.exec(statement)
            return result.all(), None
        except Exception as e:
            return [], error(str(e))

    async def update_user(self, *, user: User) -> Tuple[Optional[User], Error]:
        err = await user.save(self.session)
        if err:
            return None, err
        return user, None

    async def delete_user(self, *, user_id: UUID) -> Error:
        user, err = await self.get_user_by_id(user_id=user_id)
        if err:
            return err
        return await user.delete(self.session)

    async def create_user_profile(
        self, *, user_profile: UserProfile
    ) -> Tuple[Optional[UserProfile], Error]:
        return await user_profile.create(self.session)

    async def get_user_profile_by_user_id(
        self, *, user_id: UUID
    ) -> Tuple[Optional[UserProfile], Error]:
        profile = await UserProfile.find_one(self.session, user_id=user_id)
        if not profile:
            return None, error("User profile not found")
        return profile, None

    async def update_user_profile(self, *, user_profile: UserProfile) -> Tuple[Optional[UserProfile], Error]:
        err = await user_profile.save(self.session)
        if err:
            return None, err
        return user_profile, None