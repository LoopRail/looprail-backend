from typing import List, Optional, Tuple

from src.infrastructure.repositories.base import Base
from src.models.wallet_model import Asset
from src.types.common_types import WalletId
from src.types.error import Error


class AssetRepository(Base[Asset]):
    """
    Concrete implementation of the asset repository using SQLModel.
    """

    _model = Asset

    async def get_assets_by_wallet_id(
        self, wallet_id: WalletId
    ) -> Tuple[List[Asset], Error]:
        assets = await self.find_all(wallet_id=wallet_id)
        return assets, None

    async def create_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await self.create(asset)

    async def update_asset(self, *, asset: Asset) -> Tuple[Optional[Asset], Error]:
        return await self.update(asset)
