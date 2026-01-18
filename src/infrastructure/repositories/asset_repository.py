from typing import List, Optional, Tuple

from src.infrastructure.repositories.base import Base
from src.models.wallet_model import Asset
from src.types import AssetType
from src.types.common_types import WalletId
from src.types.error import Error, error


class AssetRepository(Base):
    """
    Concrete implementation of the asset repository using SQLModel.
    """

    async def get_asset_by_wallet_id_and_asset_id(
        self, *, wallet_id: WalletId, asset_id: AssetType
    ) -> Tuple[Optional[Asset], Error]:
        found_asset, err = await self.find_one(Asset, wallet_id=wallet_id, id=asset_id)

        if err:
            return None, error(
                f"Asset with ID {asset_id} not found for wallet {wallet_id}, Error {err.message}"
            )
        return found_asset, None

    async def get_assets_by_wallet_id(
        self, wallet_id: WalletId
    ) -> Tuple[List[Asset], Error]:
        assets = await self.find_all(Asset, wallet_id=wallet_id)
        return assets, None

    async def create_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await self.create(asset)

    async def update_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await self.update(asset)
