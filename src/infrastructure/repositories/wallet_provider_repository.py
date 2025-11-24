from typing import Optional, Tuple
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from src.models import WalletProvider
from src.types.error import Error, error
from src.types.types import Provider as ProviderEnum


class WalletProviderRepository:
    """
    Concrete implementation of the provider repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(
        self, *, provider_id: UUID
    ) -> Tuple[Optional[WalletProvider], Error]:
        provider = await WalletProvider.get(self.session, provider_id)
        if not provider:
            return None, error("Provider not found")
        return provider, None

    async def get_by_name(
        self, *, name: ProviderEnum, **kwargs
    ) -> Tuple[Optional[WalletProvider], Error]:
        provider = await WalletProvider.find_one(self.session, name=name, **kwargs)
        if not provider:
            return None, error("Provider not found")
        return provider, None

    async def delete(self, *, provider_id: UUID) -> Error:
        provider, err = await self.get_by_id(provider_id=provider_id)
        if err:
            return err
        return await provider.delete(self.session)
