from typing import Optional, Tuple
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models.wallet_model import Asset
from src.types import AssetType
from src.types.error import Error, error


class AssetRepository:
    """
    Concrete implementation of the asset repository using SQLModel.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_asset_by_wallet_id_and_asset_type(
        self, *, wallet_id: UUID, asset_type: UUID 
    ) -> Tuple[Optional[Asset], Error]:
        asset = await self.session.exec(
            select(Asset)
            .where(Asset.wallet_id == wallet_id)
            .where(Asset.asset_id == asset_type)
        )
        found_asset = asset.first()
        if not found_asset:
            return None, error(f"Asset with type {asset_type} not found for wallet {wallet_id}")
        return found_asset, None

    async def create_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await asset.create(self.session)

    async def update_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        err = await asset.save(self.session)
        if err:
            return None, err
        return asset, None
