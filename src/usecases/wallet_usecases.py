from typing import Optional, Self, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import AssetRepository, UserRepository, WalletRepository
from src.infrastructure.services import LedgerService, WalletManager
from src.infrastructure.settings import BlockRaderConfig, LedgderServiceConfig
from src.models import Asset, User, Wallet # Added Asset import
from src.types import AssetType, Chain, Error, IdentiyType, Provider, error # Added AssetType import
from src.types.blnk import (BalanceResponse, CreateBalanceRequest,
                            CreateIdentityRequest, IdentityResponse)
from src.types.blockrader import CreateAddressRequest, WalletAddressResponse

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
        asset_repository: AssetRepository,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.provider = provider

        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.asset_repository = asset_repository

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

    async def _get_user_data(self, user_id: UUID) -> Tuple[Optional[User], Error]:
        user, err = await self.service.user_repository.get_user_by_id(user_id)
        if err:
            logger.error("Could not get user %s Error: %s", user_id, err.message)
            return None, error("Could not get user")
        return user, None

    async def _create_ledger_identity(
        self, user: User
    ) -> Tuple[Optional[IdentityResponse], Error]:
        identity_request = CreateIdentityRequest(
            identity_type=IdentiyType.INDIVIDUAL,
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
        return ledger_identity, None

    async def _update_user_ledger_identity(
        self, user: User, ledger_identity_id: str
    ) -> Optional[Error]:
        user.ledger_identiy_id = ledger_identity_id
        _, err = await self.service.user_repository.update_user(user)
        if err:
            logger.error(
                "Could not update user with ledger identity ID %s Error: %s",
                user.id,
                err.message,
            )
            return error("Could not update user with ledger identity ID")
        return None

    async def _generate_provider_wallet(
        self, user_id: UUID
    ) -> Tuple[Optional[WalletAddressResponse], Error]:
        wallet_request = CreateAddressRequest(
            name=f"wallet:customer:{user_id}",
            disableAutoSweep=True,
            metadata={"user_id": user_id},
        )
        provider_wallet, err = await self.manager.generate_address(wallet_request)
        if err:
            logger.error("Could not generate blockrader wallet %s", err.message)
            return None, error("Could not generate wallet")
        return provider_wallet, None

    async def _create_local_wallet(
        self, user: User, provider_wallet: WalletAddressResponse
    ) -> Tuple[Optional[Wallet], Error]:
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
            name=f"wallet:customer:{user.id}",
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

    async def _create_ledger_balance(
        self, user: User, local_wallet: Wallet
    ) -> Tuple[Optional[BalanceResponse], Error]:
        if (
            not self.service.ledger_service.config.ledgers
            or not self.service.ledger_service.config.ledgers.ledgers
        ):
            return None, error("Ledger configuration not found")

        ledger_config = self.service.ledger_service.config.ledgers.ledgers[
            0
        ]  # TODO add get method here to get the ledger with a specifc name

        currency = "USD" # Default currency
        asset_type = AssetType.USDC # Default asset type

        # Attempt to derive asset type from local_wallet if it exists
        if hasattr(local_wallet, "asset_type") and local_wallet.asset_type:
            try:
                asset_type = AssetType(local_wallet.asset_type.value)
                currency = local_wallet.asset_type.value
            except ValueError:
                logger.warning(
                    "Invalid asset_type found in local_wallet: %s. Defaulting to USDC.",
                    local_wallet.asset_type.value,
                )

        balance_request = CreateBalanceRequest(
            ledger_id=ledger_config.ledger_id,
            identity_id=user.ledger_identiy_id,
            currency=currency,
        )
        ledger_balance, err = await self.service.ledger_service.balances.create_balance(
            balance_request
        )
        if err:
            logger.error(
                "Could not create ledger balance for wallet %s Error: %s",
                local_wallet.id,
                err.message,
            )
            return None, error("Could not create ledger balance")

        # Create Asset record in local DB
        new_asset = Asset(
            wallet_id=local_wallet.id,
            ledger_balance_id=ledger_balance.balance_id,
            name=f"{asset_type.value} for {local_wallet.address}",
            asset_id=asset_type,
            address=local_wallet.address,  # This might be the contract address for the token
            symbol=asset_type.value,
            decimals=6,  # Default for USDC, should be dynamic
            network=local_wallet.chain.value,
        )
        _, err = await self.service.asset_repository.create_asset(asset=new_asset)
        if err:
            logger.error(
                "Could not create local asset record for wallet %s, asset %s Error: %s",
                local_wallet.id,
                asset_type.value,
                err.message,
            )
            return None, error("Could not create local asset record")

        return ledger_balance, None



    async def create_user_wallet(self, user_id: UUID) -> Tuple[Optional[Self], Error]:
        user, err = await self._get_user_data(user_id)
        if err:
            return None, err

        ledger_identity, err = await self._create_ledger_identity(user)
        if err:
            return None, err

        err = await self._update_user_ledger_identity(user, ledger_identity.identity_id)
        if err:
            return None, err

        provider_wallet, err = await self._generate_provider_wallet(user.id)
        if err:
            return None, err

        wallet, err = await self._create_local_wallet(user, provider_wallet)
        if err:
            return None, err

        ledger_balance, err = await self._create_ledger_balance(user, wallet)
        if err:
            return None, err

        return wallet, None
