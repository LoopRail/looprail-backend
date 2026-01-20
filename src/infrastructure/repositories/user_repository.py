from typing import Optional, Tuple

from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.infrastructure.repositories.base import Base
from src.models.user_model import User, UserProfile
from src.types.common_types import UserId
from src.types.error import Error, NotFoundError, UserAlreadyExistsError, error


class UserRepository(Base):
    """
    Concrete implementation of the user repository using SQLModel.
    """

    _model = User

    async def create_user(self, *, user: User) -> Tuple[Optional[User], Error]:
        async with self.session.begin_nested():
            existing_user_by_email, err = await self.get_user_by_email(email=user.email)
            if err != NotFoundError and err:
                return None, err
            if existing_user_by_email is not None:
                return None, UserAlreadyExistsError(
                    "User with this email already exists"
                )

            existing_user_by_username, err = await self.get_user_by_username(
                username=user.username
            )

            if err != NotFoundError and err:
                return None, err
            if existing_user_by_username is not None:
                return None, UserAlreadyExistsError(
                    "User with this username already exists"
                )

            return await self.create(user)

    async def get_user_by_id(self, *, user_id: UserId) -> Tuple[Optional[User], Error]:
        # return await self.get(User, user_id)
        query = select(User).options(selectinload("*")).where(User.id == user_id)
        result = await self.session.execute(query)
        return result.scalars().first(), None

    async def get_user_by_email(
        self, *, email: EmailStr
    ) -> Tuple[Optional[User], Error]:
        query = select(User).options(selectinload("*")).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalars().first(), None

    async def get_user_by_username(
        self, *, username: str
    ) -> Tuple[Optional[User], Error]:
        query = select(User).options(selectinload("*")).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalars().first(), None

    async def list_users(
        self, *, limit: int = 50, offset: int = 0
    ) -> Tuple[list[User], Error]:
        try:
            statement = select(User).offset(offset).limit(limit)
            result = await self.session.execute(statement)
            return result.scalars().all(), None
        except SQLAlchemyError as e:
            return [], error(str(e))

    async def update_user(
        self, *, user_id: UserId, **kwargs
    ) -> Tuple[Optional[User], Error]:
        user, err = await self.get(user_id)
        if err:
            return None, err
        return await self.update(user, **kwargs)

    async def delete_user(self, *, user_id: UserId) -> Error:
        user, err = await self.get(user_id)
        if err:
            return err
        return await self.delete(user)

    async def create_user_profile(
        self, *, user_profile: UserProfile
    ) -> Tuple[Optional[UserProfile], Error]:
        return await self.create(user_profile)

    async def get_user_profile_by_user_id(
        self, *, user_id: UserId
    ) -> Tuple[Optional[UserProfile], Error]:
        user, err = await self.get(user_id)
        if err:
            return None, err

        stmt = select(UserProfile).where(UserProfile.id == user.profile.id)
        result = await self.session.execute(stmt)
        return result.scalars().first(), None

    async def update_user_profile(
        self, *, user_id: UserId, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        user_profile, err = await self.get_user_profile_by_user_id(user_id=user_id)
        if err:
            return None, err
        return await self.update(user_profile, **kwargs)
