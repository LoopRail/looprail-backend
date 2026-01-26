from typing import Optional, Tuple

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories.base import Base
from src.models.wallet_model import Wallet
from src.types.common_types import UserId
from src.types.error import Error

logger = get_logger(__name__)


class WalletRepository(Base[Wallet]):
    """
    Concrete implementation of the wallet repository using SQLModel.
    """

    _model = Wallet

    async def get_wallet_by_address(
        self, *, address: str
    ) -> Tuple[Optional[Wallet], Error]:
        return await self.find_one(address=address)

    async def get_wallet_by_provider_id(
        self, *, provider_id: str
    ) -> Tuple[Optional[Wallet], Error]:
        return await self.find_one(provider_id=provider_id)

    async def get_wallet_by_user_id(
        self, *, user_id: UserId
    ) -> Tuple[Optional[Wallet], Error]:
        return await self.find_one(user_id=user_id)
