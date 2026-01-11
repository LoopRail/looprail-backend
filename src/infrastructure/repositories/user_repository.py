from typing import Optional, Tuple
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.user_model import User, UserProfile
from src.types.error import Error, error


class UserRepository:
    """
    Concrete implementation of the user repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> Error:
        return await user.save(self.session)

    async def create_user(self, *, user: User) -> Tuple[Optional[User], Error]:
        return await user.create(self.session)

    async def get_user_by_id(self, *, user_id: UUID) -> Tuple[Optional[User], Error]:
        return await User.get(self.session, user_id)

    async def get_user_by_email(
        self, *, email: EmailStr
    ) -> Tuple[Optional[User], Error]:
        return await User.find_one(self.session, email=email)

    async def list_users(
        self, *, limit: int = 50, offset: int = 0
    ) -> Tuple[list[User], Error]:
        try:
            statement = select(User).offset(offset).limit(limit)
            result = await self.session.exec(statement)
            return await result.all(), None
        except SQLAlchemyError as e:
            return [], error(str(e))

    async def update_user(
        self, *, user_id: UUID, **kwargs
    ) -> Tuple[Optional[User], Error]:
        user, err = await self.get_user_by_id(user_id=user_id)
        if err:
            return None, err
        return await user.update(self.session, **kwargs)

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
        user, err = await self.get_user_by_id(user_id=user_id)
        if err:
            return None, err
        return await UserProfile.get(self.session, _id=user.profile.id)

    async def update_user_profile(
        self, *, user_id: UUID, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        user_profile, err = await self.get_user_profile_by_user_id(user_id=user_id)
        if err:
            return None, err
        return await user_profile.update(self.session, **kwargs)
