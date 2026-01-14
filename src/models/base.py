from datetime import datetime
from typing import ClassVar, List, Optional, Self, Tuple
from uuid import UUID, uuid4

from asyncpg.exceptions import UniqueViolationError
from pydantic import ConfigDict
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import Select
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.logger import get_logger
from src.types.common_types import DeletionFilter
from src.types.error import (Error, ItemDoesNotExistError, NotFoundError,
                             ProtectedModelError, UpdatingProtectedFieldError,
                             error)

logger = get_logger(__name__)
__default_protected_fields__ = ["id", "created_at", "updated_at", "deleted_at"]


async def exec_stmt[T](
    session: AsyncSession,
    stmt: Select,
    *,
    one: bool = False,
) -> Optional[T] | List[T]:
    """
    Execute a SQLAlchemy statement and return ORM results.
    """
    result = await session.execute(stmt)
    scalars = result.scalars()

    if one:
        return scalars.first()

    return scalars.all()


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
        except UniqueViolationError as e:
            await session.rollback()
            logger.error(e, stack_info=True)
            return error(e)
        except (IntegrityError, SQLAlchemyError) as e:
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
        cls,
        session: AsyncSession,
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> List["Self"]:
        stmt = select(cls).filter_by(**kwargs)

        if deletion == "active":
            stmt = stmt.where(cls.deleted_at.is_(None))
        elif deletion == "deleted":
            stmt = stmt.where(cls.deleted_at.is_not(None))

        return await exec_stmt(session, stmt)

    @classmethod
    async def find_one(
        cls,
        session: AsyncSession,
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> tuple[Optional["Self"], Optional[Error]]:
        stmt = select(cls).filter_by(**kwargs)

        if deletion == "active":
            stmt = stmt.where(cls.deleted_at.is_(None))
        elif deletion == "deleted":
            stmt = stmt.where(cls.deleted_at.is_not(None))

        obj = await exec_stmt(session, stmt, one=True)

        if obj is None:
            return None, NotFoundError

        return obj, None

    @classmethod
    async def get(
        cls,
        session: AsyncSession,
        _id: str,
        deletion: DeletionFilter = "active",
    ) -> tuple[Optional["Self"], Optional[Error]]:
        return await cls.find_one(session, deletion, id=_id)


class Base(SQLModel, DatabaseMixin):
    __id_prefix__: ClassVar[str] = None
    __protected_fields__: ClassVar[str | List[str]] = None
    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, populate_by_name=True
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)

    def _get_protected_fields(self) -> str | list["str"]:
        return self.__protected_fields__

    def _is_protected(self) -> bool:
        protected_fields = self._get_protected_fields()
        return isinstance(protected_fields, str) and (protected_fields.lower() == "all")

    def on_delete(self):
        return None

    @classmethod
    def get_id_prefix(cls) -> str:
        return cls.__id_prefix__ if cls.__id_prefix__ else ""

    def get_prefixed_id(self) -> str:
        prefix = self.get_id_prefix()
        return f"{prefix}{self.id}"
