from typing import List, Optional, Tuple, Type, TypeVar, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.logger import get_logger
from src.types.common_types import DeletionFilter
from src.types.error import Error, error

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=SQLModel)


class Base:
    _model: Type[ModelType] | None = None

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @classmethod
    def _get_model(cls) -> Type[ModelType]:
        if cls._model is None:
            raise RuntimeError(
                f"{cls.__name__} has no model configured. Set _model on the subclass."
            )
        return cls._model

    async def rollback(self) -> Error:
        try:
            await self.session.rollback()
            logger.debug("Successfully performed session rollback.")
            return None
        except SQLAlchemyError as e:
            logger.error("Session rollback failed: %s", str(e))
            return error(e)

    async def save(self, instance: ModelType):
        logger.debug("Saving instance of %s", type(instance).__name__)
        return await instance.save(self.session)

    async def get(
        self,
        _id: Union[str, int],
        deletion: DeletionFilter = "active",
    ) -> Tuple[Optional[ModelType], Error]:
        logger.debug("Retrieving %s with ID: %s", self._get_model().__name__, _id)
        return await self._get_model().get(self.session, _id, deletion)

    async def find_one(
        self,
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> Tuple[Optional[ModelType], Error]:
        logger.debug("Finding one %s with criteria: %s", self._get_model().__name__, kwargs)
        return await self._get_model().find_one(self.session, deletion, **kwargs)

    async def find_all(
        self,
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> List[ModelType]:
        return await self._get_model().find_all(self.session, deletion, **kwargs)

    async def create(self, instance: ModelType) -> Tuple[Optional[ModelType], Error]:
        logger.debug("Creating new %s", type(instance).__name__)
        return await instance.create(self.session)

    async def update(
        self, instance: ModelType, **kwargs
    ) -> Tuple[Optional[ModelType], Error]:
        logger.debug("Updating %s (ID: %s) with data: %s", type(instance).__name__, getattr(instance, 'id', 'unknown'), kwargs)
        return await instance.update(self.session, **kwargs)

    async def delete(self, instance: ModelType) -> Error:
        logger.debug("Deleting %s (ID: %s)", type(instance).__name__, getattr(instance, 'id', 'unknown'))
        return await instance.delete(self.session)
