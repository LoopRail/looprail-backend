from datetime import UTC, datetime, timezone
from typing import ClassVar, List, Optional, Self, Tuple, Type
from uuid import UUID, uuid4

from asyncpg.exceptions import UniqueViolationError
from pydantic import ConfigDict, field_serializer
from sqlalchemy import DateTime
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.sql import Select
from sqlalchemy.orm import selectinload
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.logger import get_logger
from src.types.common_types import DeletionFilter
from src.types.error import (
    Error,
    ItemDoesNotExistError,
    NotFoundError,
    ProtectedModelError,
    UpdatingProtectedFieldError,
    error,
)

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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DatabaseMixin:
    async def create(self, session: AsyncSession) -> Tuple[Optional[Self], Error]:
        err = await self.save(session)
        if err:
            return None, err
        return self, None

    async def save(self, session: AsyncSession) -> Error:
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
        self.updated_at = datetime.now(UTC)
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
    async def find_one[T](
        cls: Type[T],
        session: AsyncSession,
        filters: dict = {},
        deletion: Optional[str] = None,
        load: Optional[List[str]] = None,
    ) -> Tuple[Optional[T], Optional[Exception]]:
        """
        Generic async find_one for any model inheriting AsyncMixin.

        Args:
            session: AsyncSession
            filters: dict of field=value to filter
            deletion: "active" | "deleted" | None
            load: list of relationship names to eager load via selectinload

        Returns:
            Tuple[object_or_None, error_or_None]
        """
        stmt = select(cls).filter_by(**filters)

        # Optional deletion filter
        if deletion == "active":
            if hasattr(cls, "deleted_at"):
                stmt = stmt.where(cls.deleted_at.is_(None))
        elif deletion == "deleted":
            if hasattr(cls, "deleted_at"):
                stmt = stmt.where(cls.deleted_at.is_not(None))

        # Optional dynamic eager loading
        if load:
            for rel_name in load:
                if hasattr(cls, rel_name):
                    stmt = stmt.options(selectinload(getattr(cls, rel_name)))

        # Execute query
        result = await session.execute(stmt)
        obj = result.scalar_one_or_none()

        if obj is None:
            return None, NotFoundError

        return obj, None

    @classmethod    
    async def get(
        cls,
        session: AsyncSession,
        _id: str,
        deletion: Optional[str] = "active",
        load: Optional[List[str]] = None,  # relationships to eager-load
    ) -> Tuple[Optional["Self"], Optional[Exception]]:
        """
        Fetch a single object by ID, optionally eager-loading relationships.

        Args:
            session: AsyncSession
            _id: The primary key
            deletion: "active" | "deleted" | None
            load: list of relationship names to eager-load dynamically

        Returns:
            Tuple[obj_or_None, error_or_None]
        """
        filters = {"id": _id}
        obj, err = await cls.find_one(
            session=session,
            filters=filters,
            deletion=deletion,
            load=load,
        )
        return obj, err


class Base(SQLModel, DatabaseMixin):
    __id_prefix__: ClassVar[str] = None
    __protected_fields__: ClassVar[str | List[str]] = None
    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, populate_by_name=True
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

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

    @field_serializer("id")
    def serialize_id(self, _: UUID) -> str:
        return self.get_prefixed_id()
