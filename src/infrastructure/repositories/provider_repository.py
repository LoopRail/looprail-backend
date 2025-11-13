from typing import Optional, Tuple
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.repositories.base_repository import BaseRepository
from src.models.wallet_model import Provider
from src.types.error import Error, error
from src.types.types import Provider as ProviderEnum


class ProviderRepository(BaseRepository):
    """
    Concrete implementation of the provider repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, *, provider_id: UUID) -> Tuple[Optional[Provider], Error]:
        provider = await Provider.get(self.session, provider_id)
        if not provider:
            return None, error("Provider not found")
        return provider, None

    async def get_by_name(self, *, name: ProviderEnum) -> Tuple[Optional[Provider], Error]:
        provider = await Provider.find_one(self.session, name=name)
        if not provider:
            return None, error("Provider not found")
        return provider, None

    async def delete(self, *, provider_id: UUID) -> Error:
        provider, err = await self.get_by_id(provider_id=provider_id)
        if err:
            return err
        return await provider.delete(self.session)
