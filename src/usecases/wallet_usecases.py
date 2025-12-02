from typing import Optional, Self, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import UserRepository, WalletRepository
from src.infrastructure.services.blockrader_client import AddressManager, WalletManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import Wallet
from src.types import Chain, Error, Provider, error
from src.types.blockrader import CreateAddressRequest

logger = get_logger(__name__)


class TransactionMixin:
    async def transfer(self, amount: str, destination_address: str):
        pass


class WalletService:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.provider = provider

        self.user_repository = user_repository
        self.wallet_repository = wallet_repository

        self._manager: Optional[WalletManager] = None
        self._manager_id: Optional[str] = None

    #
    # def new_address_manager(self, address_id: str):
    #     self._manager_id = address_id
    #     self._manager = AddressManager(
    #         self.blockrader_config, self._manager, address_id
    #     )
    #     return self

    def new_wallet_manager(
        self, wallet_id: str, chain: Chain
    ) -> "WalletManagerUsecase":
        self._manager_id = wallet_id
        self._manager = WalletManager(self.blockrader_config, wallet_id)
        manager_usecase = WalletManagerUsecase(
            self, self._manager_id, self._manager, chain
        )
        return manager_usecase


class WalletManagerUsecase(TransactionMixin):
    def __init__(
        self,
        service: WalletService,
        wallet_id: str,
        manager: WalletManager,
        chain: Chain,
    ) -> None:
        self.service = service
        self.manager = manager
        self.wallet_id = wallet_id
        self.chain = chain

    async def create_user_wallet(self, user_id: UUID) -> Tuple[Optional[Self], Error]:
        user, err = await self.service.user_repository.get_user_by_id(user_id)
        if err:
            logger.error("Could not get user %s Error: %s", user_id, err.message)
            return None, error("Could not get user")

        wallet_request = CreateAddressRequest(
            name=f"wallet:customer:{user.id}", disableAutoSweep=True
        )
        provider_wallet, err = await self.manager.generate_address(wallet_request)
        if err:
            logger.error("Could not generate blockrader wallet %s", err.message)
            return None, error("Could not generate wallet")
        provider, err = await self.service.wallet_provider_repository.get_by_name(
            self.service.provider, is_active=True
        )
        if err:
            logger.error(
                "Could not get wallet provider %s Error: %s",
                self.service.provider,
                err.message,
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

        wallet, err = await self.service.wallet_repository.create_wallet(new_wallet)
        if err:
            logger.error(
                "Could not save wallet %s on provider %s to db Error: %s",
                provider_wallet.data.data_id,
                self.service.provider.name,
                err.message,
            )
            return None, err("Could not get wallet Provider")
        return wallet, None


class AddressManagerUsecase:
    def __init__(self) -> None:
        pass


# TODO we still need to make some fixes her but leave that for later
