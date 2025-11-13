from typing import Optional, Self, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (UserRepository,
                                             WalletProviderRepository,
                                             WalletRepository)
from src.infrastructure.services.blockrader_client import (AddressManager,
                                                           WalletManager)
from src.infrastructure.settings import BlockRaderConfig
from src.models import Wallet
from src.types import (Chain, Error, Provider,
                       WalletManagerNotInitializedError, error)
from src.types.blockrader import CreateAddressRequest

logger = get_logger(__name__)


class WalletService:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        wallet_provider_repository: WalletProviderRepository,
        chain: Chain = Chain.BASE,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.provider = provider
        self.chain = chain

        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.wallet_provider_repository = wallet_provider_repository

        self.wallet_id: Optional[str] = None
        self.address_id: Optional[str] = None

        self.wallet_manager: Optional[WalletManager] = None
        self.address_manager: Optional[AddressManager] = None

    def new_address_manager(self, address_id: str):
        self.address_id = address_id
        self.address_manager = AddressManager(
            self.blockrader_config, self.wallet_id, address_id
        )
        return self

    def new_wallet_manager(self, wallet_id) -> Self:
        self.wallet_id = wallet_id
        self.wallet_manager = WalletManager(self.blockrader_config, wallet_id)
        return self

    async def create_user_wallet(self, user_id: UUID) -> Tuple[Optional[Self], Error]:
        user, err = await self.user_repository.get_user_by_id(user_id)
        if err:
            logger.error("Could not get user %s Error: %s", user_id, err.message)
            return None, error("Could not get user")
        if self.wallet_manager is None:
            raise WalletManagerNotInitializedError(
                "Wallet manager must be set before use."
            )
        wallet_request = CreateAddressRequest(
            name=f"wallet:customer:{user.id}", disableAutoSweep=True
        )
        provider_wallet, err = await self.wallet_manager.generate_address(
            wallet_request
        )
        if err:
            logger.error("Could not generate blockrader wallet %s", err.message)
            return None, error("Could not generate wallet")
        provider, err = await self.wallet_provider_repository.get_by_name(
            self.provider, is_active=True
        )
        if err:
            logger.error(
                "Could not get wallet provider %s Error: %s", self.provider, err.message
            )
            return None, err("Could not get wallet Provider")
        new_wallet = Wallet(
            user_id=user.id,
            addess=provider_wallet.data.address,
            Chain=self.chain,
            provider_id=provider.id,
            name=wallet_request.name,
            derivation_path=provider_wallet.data.derivationPath,
        )

        wallet, err = await self.wallet_repository.create_wallet(new_wallet)
        if err:
            logger.error(
                "Could not save wallet %s on provider %s to db Error: %s",
                provider_wallet.data.data_id,
                self.provider.name,
                err.message,
            )
            return None, err("Could not get wallet Provider")
        return wallet, None

    async def transfer(self, amount: str, destination_address: str):
        pass
