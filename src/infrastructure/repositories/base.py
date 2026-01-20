from typing import List, Optional, Tuple, Type, TypeVar, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.types.common_types import DeletionFilter
from src.types.error import Error, error

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
            return None
        except SQLAlchemyError as e:
            return error(e)

    async def save(self, instance: ModelType):
        return await instance.save(self.session)

    async def get(
        self,
        _id: Union[str, int],
        deletion: DeletionFilter = "active",
    ) -> Tuple[Optional[ModelType], Error]:
        return await self._get_model().get(self.session, _id, deletion)

    async def find_one(
        self,
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> Tuple[Optional[ModelType], Error]:
        return await self._get_model().find_one(self.session, deletion, **kwargs)

    async def find_all(
        self,
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> List[ModelType]:
        return await self._get_model().find_all(self.session, deletion, **kwargs)

    async def create(self, instance: ModelType) -> Tuple[Optional[ModelType], Error]:
        return await instance.create(self.session)

    async def update(
        self, instance: ModelType, **kwargs
    ) -> Tuple[Optional[ModelType], Error]:
        return await instance.update(self.session, **kwargs)

    async def delete(self, instance: ModelType) -> Error:
        return await instance.delete(self.session)
