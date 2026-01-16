from typing import Optional, Tuple

from sqlmodel import select

from src.infrastructure.repositories.base import Base
from src.models.wallet_model import Asset
from src.types import AssetType
from src.types.common_types import WalletId
from src.types.error import Error, error


class AssetRepository(Base):
    """
    Concrete implementation of the asset repository using SQLModel.
    """

    async def get_asset_by_wallet_id_and_asset_type(
        self, *, wallet_id: WalletId, asset_type: AssetType
    ) -> Tuple[Optional[Asset], Error]:
        asset = await self.session.execute(
            select(Asset)
            .where(Asset.wallet_id == wallet_id)
            .where(Asset.asset_id == asset_type)
        )
        found_asset = asset.first()
        if not found_asset:
            return None, error(
                f"Asset with type {asset_type} not found for wallet {wallet_id}"
            )
        return found_asset, None

    async def create_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await self.create(asset)

    async def update_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await self.update(asset)
