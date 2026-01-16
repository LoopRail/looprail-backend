from typing import List, Optional, Tuple, Type, TypeVar, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.types.common_types import DeletionFilter
from src.types.error import Error, error

ModelType = TypeVar("ModelType", bound=SQLModel)


class Base:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def rollback(self) -> Error:
        try:
            await self.session.rollback()
            return None
        except SQLAlchemyError as e:
            return error(e)

    async def save(self, model: Type[ModelType]):
        return await model.save(self.session)

    async def get(
        self,
        model: Type[ModelType],
        _id: Union[str, int],
        deletion: DeletionFilter = "active",
    ) -> Tuple[Optional[ModelType], Error]:
        return await model.get(self.session, _id, deletion)

    async def find_one(
        self,
        model: Type[ModelType],
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> Tuple[Optional[ModelType], Error]:
        return await model.find_one(self.session, deletion, **kwargs)

    async def find_all(
        self,
        model: Type[ModelType],
        deletion: Optional[DeletionFilter] = None,
        **kwargs,
    ) -> List[ModelType]:
        return await model.find_all(self.session, deletion, **kwargs)

    async def create(self, instance: ModelType) -> Tuple[Optional[ModelType], Error]:
        return await instance.create(self.session)

    async def update(
        self, instance: ModelType, **kwargs
    ) -> Tuple[Optional[ModelType], Error]:
        return await instance.update(self.session, **kwargs)

    async def delete(self, instance: ModelType) -> Error:
        return await instance.delete(self.session)
