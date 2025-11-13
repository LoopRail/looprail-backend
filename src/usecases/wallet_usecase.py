from typing import Optional, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import WalletRepository
from src.infrastructure.services.blockrader_client import WalletManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import Wallet
from src.types import Error, error
from src.types.blockrader import CreateAddressRequest

logger = get_logger(__name__)


class WalletUseCase:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        wallet_repository: WalletRepository,
        wallet_id: UUID,
    ):
        self.blockrader_config = blockrader_config
        self.wallet_repository = wallet_repository
        self.wallet_id = wallet_id
        self.wallet_manager = WalletManager(self.blockrader_config, str(wallet_id))

    async def get_wallet_details(self) -> Tuple[Optional[Wallet], Error]:
        wallet, err = await self.wallet_repository.get_wallet_by_id(
            wallet_id=self.wallet_id
        )
        if err:
            logger.error("Could not get wallet %s Error: %s", self.wallet_id, err.message)
            return None, error("Could not get wallet details")
        return wallet, None

    async def create_address(
        self, address_request: CreateAddressRequest
    ) -> Tuple[Optional[Wallet], Error]:
        # This method would typically interact with the wallet_manager
        # to create a new address within this wallet.
        # For now, let's assume it's a placeholder or will be implemented later.
        pass

    async def transfer_asset(self, amount: str, destination_address: str):
        # This method would typically interact with the wallet_manager
        # to perform a transfer.
        pass
