from datetime import datetime
from typing import Optional, Self, Tuple
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure import get_logger
from src.types import Error, error

logger = get_logger(__name__)


class DatabaseMixin:
    async def create(
        self: "Base", session: AsyncSession
    ) -> Tuple[Optional[Self], Error]:
        err = self.save(session)
        if err:
            return None, err
        return self, None

    async def save(self, session: AsyncSession) -> error:
        try:
            session.add(self)
            session.flush()
            session.refresh(self)
            return None
        except IntegrityError as e:
            session.rollback()
            logger.error(e, stack_info=True)
            return error(e)
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(e, stack_info=True)
            return error(e)


class Base(SQLModel, DatabaseMixin, table=True):
    model_config = ConfigDict(
        use_enum_values=True, validate_assignment=True, populate_by_name=True
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None
