from typing import Optional, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import WalletProviderRepository, WalletRepository
from src.infrastructure.services.blockrader_client import WalletManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import Wallet
from src.types import Chain, Error, Provider, error
from src.types.blockrader import CreateAddressRequest

logger = get_logger(__name__)


class WalletManagerUseCase:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        wallet_repository: WalletRepository,
        wallet_provider_repository: WalletProviderRepository,
        chain: Chain = Chain.BASE,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.provider = provider
        self.chain = chain

        self.wallet_repository = wallet_repository
        self.wallet_provider_repository = wallet_provider_repository

        self.wallet_manager: Optional[WalletManager] = None

    def new_wallet_manager(self, wallet_id: UUID):
        self.wallet_manager = WalletManager(self.blockrader_config, str(wallet_id))
        return self

    async def generate_address(
        self, wallet_request: CreateAddressRequest
    ) -> Tuple[Optional[Wallet], Error]:
        if self.wallet_manager is None:
            return None, error("Wallet manager not initialized.")

        provider_wallet, err = await self.wallet_manager.generate_address(
            wallet_request
        )
        if err:
            logger.error("Could not generate blockrader wallet %s", err.message)
            return None, error("Could not generate wallet")

        provider_model, err = await self.wallet_provider_repository.get_by_name(
            name=self.provider
        )
        if err:
            logger.error(
                "Could not get wallet provider %s Error: %s", self.provider, err.message
            )
            return None, error("Could not get wallet Provider")

        new_wallet = Wallet(
            user_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
            address=provider_wallet.data.address,
            chain=self.chain,
            provider_id=provider_model.id,
            name=wallet_request.name,
            derivation_path=provider_wallet.data.derivationPath,
        )

        wallet, err = await self.wallet_repository.create_wallet(wallet=new_wallet)
        if err:
            logger.error(
                "Could not save wallet %s on provider %s to db Error: %s",
                provider_wallet.data.data_id,
                self.provider.value,
                err.message,
            )
            return None, error("Could not save wallet")
        return wallet, None
