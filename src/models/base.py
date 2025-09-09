from datetime import datetime
from typing import Optional, Self, Tuple
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.logger import get_logger
from src.types.error import Error, error

logger = get_logger(__name__)


class DatabaseMixin:
    async def create(
        self: "Base", session: AsyncSession
    ) -> Tuple[Optional[Self], Error]:
        err = await self.save(session)
        if err:
            return None, err
        return self, None

    async def save(self, session: AsyncSession) -> error:
        try:
            session.add(self)
            await session.flush()
            await session.refresh(self)
            await session.commit()
            return None
        except IntegrityError as e:
            await session.rollback()
            logger.error(e, stack_info=True)
            return error(e)
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(e, stack_info=True)
            return error(e)

    async def update(
        self: "Base", session: AsyncSession, **kwargs
    ) -> Tuple[Optional[Self], Error]:
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        err = await self.save(session)
        if err:
            return None, err
        return self, None

    async def delete(self, session: AsyncSession) -> error:
        self.deleted_at = datetime.utcnow()
        err = await self.save(session)
        return err

    @classmethod
    async def get(cls, session: AsyncSession, _id: UUID) -> Optional[Self]:
        return await session.get(cls, _id)

    @classmethod
    async def find_one(cls, session: AsyncSession, **kwargs) -> Optional[Self]:
        statement = select(cls).filter_by(**kwargs)
        result = await session.exec(statement)
        return result.first()

    @classmethod
    async def find_all(cls, session: AsyncSession, **kwargs) -> list[Self]:
        statement = select(cls).filter_by(**kwargs)
        result = await session.exec(statement)
        return result.all()


class Base(SQLModel, DatabaseMixin):
    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, populate_by_name=True
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None
