from typing import Optional, Self, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import WalletRepository
from src.infrastructure.services.blockrader_client import AddressManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import Wallet
from src.types import Error, error

logger = get_logger(__name__)


class AddressManagerUseCase:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        wallet_repository: WalletRepository,
        wallet_id: UUID,
        address_id: UUID,
    ):
        self.blockrader_config = blockrader_config
        self.wallet_repository = wallet_repository
        self.wallet_id = wallet_id
        self.address_id = address_id

        self.address_manager: Optional[AddressManager] = None
        self.new_address_manager(str(wallet_id), str(address_id))

    def new_address_manager(self, wallet_id: str, address_id: str):
        self.address_manager = AddressManager(
            self.blockrader_config, wallet_id, address_id
        )
        return self

    async def get_address_details(self) -> Tuple[Optional[Wallet], Error]:
        if self.address_manager is None:
            return None, error("Address manager not initialized.")
        
        # Example: Fetch address details from BlockRader
        # For now, just return the wallet from our DB
        wallet, err = await self.wallet_repository.get_wallet_by_id(wallet_id=self.wallet_id)
        if err:
            logger.error("Could not get wallet %s Error: %s", self.wallet_id, err.message)
            return None, error("Could not get wallet details")
        return wallet, None

    async def transfer(self, amount: str, destination_address: str):
        # Example: Implement transfer logic using address_manager
        pass
