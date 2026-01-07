from typing import Optional, Self, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import UserRepository, WalletRepository
from src.infrastructure.services.blockrader_client import WalletManager
from src.infrastructure.services.ledger.service import LedgerService
from src.infrastructure.settings import BlockRaderConfig, LedgderServiceConfig
from src.models import Wallet
from src.types import Chain, Error, Provider, error
from src.types.blnk.dtos import CreateBalanceRequest, CreateIdentityRequest
from src.types.blockrader import CreateAddressRequest

logger = get_logger(__name__)


class TransactionMixin:
    async def transfer(self, amount: str, destination_address: str):
        pass


class WalletService:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        ledger_service_config: LedgderServiceConfig,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.provider = provider

        self.user_repository = user_repository
        self.wallet_repository = wallet_repository

        self.ledger_service = LedgerService(ledger_service_config)

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

        # Create Ledger Identity
        identity_request = CreateIdentityRequest(
            identity_type="individual",
            first_name=user.first_name,
            last_name=user.last_name,
            email_address=user.email,
            phone_number=user.phone_number,
        )
        (
            ledger_identity,
            err,
        ) = await self.service.ledger_service.identities.create_identity(
            identity_request
        )
        if err:
            logger.error(
                "Could not create ledger identity for user %s Error: %s",
                user.id,
                err.message,
            )
            return None, error("Could not create ledger identity")

        # Update user with ledger_identity_id
        user.ledger_identiy_id = ledger_identity.identity_id
        _, err = await self.service.user_repository.update_user(user)
        if err:
            logger.error(
                "Could not update user with ledger identity ID %s Error: %s",
                user.id,
                err.message,
            )
            # TODO Potentially revert ledger identity creation here, or handle separately
            return None, error("Could not update user with ledger identity ID")

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
            address=provider_wallet.data.address,
            chain=self.chain,
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

        if (
            not self.service.ledger_service.config.ledgers
            or not self.service.ledger_service.config.ledgers.ledgers
        ):
            return None, error("Ledger configuration not found")

        ledger_config = self.service.ledger_service.config.ledgers.ledgers[
            0
        ]  # TODO add get method here to get the ledger with a specifc name

        currency = "USD"
        if hasattr(new_wallet, "asset_type") and new_wallet.asset_type:
            currency = new_wallet.asset_type.value

        balance_request = CreateBalanceRequest(
            ledger_id=ledger_config.ledger_id,
            identity_id=user.ledger_identity,
            currency=currency,
        )
        ledger_balance, err = await self.service.ledger_service.balances.create_balance(
            balance_request
        )
        if err:
            logger.error(
                "Could not create ledger balance for wallet %s Error: %s",
                wallet.id,
                err.message,
            )
            return None, error("Could not create ledger balance")

        wallet.ledger_balance_id = ledger_balance.balance_id
        _, err = await self.service.wallet_repository.update_wallet(wallet)
        if err:
            logger.error(
                "Could not update wallet with ledger balance ID %s Error: %s",
                wallet.id,
                err.message,
            )
            return None, error("Could not update wallet with ledger balance ID")

        return wallet, None
