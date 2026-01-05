from datetime import datetime
from typing import List, Optional, Self, Tuple
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.logger import get_logger
from src.types import (Error, ItemDoesNotExistError, NotFoundError,
                       ProtectedModelError, UpdatingProtectedFieldError, error)
from src.types import DeletionFilter

logger = get_logger(__name__)
__default_protected_fields__ = ["id", "created_at", "updated_at", "deleted_at"]


class DatabaseMixin:
    async def create(self, session: AsyncSession) -> Tuple[Optional[Self], Error]:
        err = await self.save(session)
        if err:
            return None, err
        return self, None

    async def save(self, session: AsyncSession) -> error:
        try:
            session.add(self)
            await session.flush()
            await session.refresh(self)
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
        protected_fields = self._get_protected_fields()
        if self._is_protected():
            return None, ProtectedModelError
        if isinstance(protected_fields, list) and any(
            key in protected_fields for key, _ in kwargs.items()
        ):
            pass
        for key, value in kwargs.items():
            if key.lower() in __default_protected_fields__:
                return None, UpdatingProtectedFieldError(key)
            if isinstance(protected_fields, list) and (key in protected_fields):
                return None, UpdatingProtectedFieldError(key)
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        err = await self.save(session)
        if err:
            return None, err
        return self, None

    async def delete(self: "Base", session: AsyncSession) -> Error:
        if self.deleted_at is not None:
            return ItemDoesNotExistError
        self.deleted_at = datetime.utcnow()
        self.on_delete()
        err = await self.save(session)
        return err

    @classmethod
    async def find_all(
        cls, session: AsyncSession, deletion: DeletionFilter = "active", **kwargs
    ) -> List["Self"]:
        statement = select(cls).filter_by(**kwargs)

        if deletion == "active":
            statement = statement.where(cls.deleted_at.is_(None))
        elif deletion == "deleted":
            statement = statement.where(cls.deleted_at.is_not(None))

        result = await session.exec(statement)
        return result.all()

    @classmethod
    async def find_one(
        cls, session: AsyncSession, deletion: DeletionFilter = "active", **kwargs
    ) -> Tuple[Optional["Self"], Error]:
        results = cls.find_all(session, deletion, **kwargs)
        if len(results) < 1:
            return None, NotFoundError
        return results[0], None

    @classmethod
    async def get(
        cls, session: AsyncSession, _id: UUID, deletion: DeletionFilter = "active"
    ) -> Tuple[Optional["Self"], Error]:
        filter_ = {"id": _id}
        result, err = cls.get(session, deletion, **filter_)
        if err:
            return None, NotFoundError
        return result, None


class Base(SQLModel, DatabaseMixin):
    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, populate_by_name=True
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = Field(default=None)

    def _get_protected_fields(self) -> str | list["str"]:
        return getattr(self, "__protected_fields__", None)

    def _is_protected(self) -> bool:
        protected_fields = self._get_protected_fields()
        return isinstance(protected_fields, str) and (protected_fields.lower() == "all")

    def on_delete(self):
        return None
