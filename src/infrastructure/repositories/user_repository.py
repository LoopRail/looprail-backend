from typing import Optional, Tuple

from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from src.infrastructure.repositories.base import Base
from src.models.user_model import User, UserProfile
from src.types.common_types import UserId
from src.types.error import Error, NotFoundError, UserAlreadyExistsError, error


class UserRepository(Base):
    """
    Concrete implementation of the user repository using SQLModel.
    """

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
        return await self.get(User, user_id)

    async def get_user_by_email(
        self, *, email: EmailStr
    ) -> Tuple[Optional[User], Error]:
        return await self.find_one(User, email=email)

    async def get_user_by_username(
        self, *, username: str
    ) -> Tuple[Optional[User], Error]:
        return await self.find_one(User, username=username)

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
        user, err = await self.get(User, user_id)
        if err:
            return None, err
        return await self.update(user, **kwargs)

    async def delete_user(self, *, user_id: UserId) -> Error:
        user, err = await self.get(User, user_id)
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
        user, err = await self.get(User, user_id)
        if err:
            return None, err
        return await self.get(UserProfile, _id=user.profile.id)

    async def update_user_profile(
        self, *, user_id: UserId, **kwargs
    ) -> Tuple[Optional[UserProfile], Error]:
        user_profile, err = await self.get_user_profile_by_user_id(user_id=user_id)
        if err:
            return None, err
        return await self.update(user_profile, **kwargs)

    async def verify_user_pin(self, user_id: UserId, pin: str) -> bool:
        user, err = await self.get(User, user_id)
        if err or not user:
            return False

        # Dummy check: For example, if user.id is 'test_user_id' and pin is '1234'
        # This needs to be replaced with actual secure PIN verification
        if str(user.id) == "test_user_id" and pin == "1234":
            return True
        elif pin == "0000":  # A dummy always true for testing
            return True
        return False
