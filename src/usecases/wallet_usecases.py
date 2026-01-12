from typing import Any, Dict, Optional, Self, Tuple

from src.dtos.wallet_dtos import TransferType, WithdrawalRequest
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (
    AssetRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, PaycrestService, WalletManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import Asset, User, Wallet
from src.types import AssetType, Error, IdentiyType, Provider, WalletConfig, error
from src.types.blnk import CreateBalanceRequest, CreateIdentityRequest, IdentityResponse
from src.types.blockrader import (
    CreateAddressRequest,
    NetworkFeeRequest,
    WalletAddressResponse,
)
from src.types.common_types import UserId
from src.types.ledger_types import Ledger
from src.usecases.transaction_usecases import TransactionUsecase

logger = get_logger(__name__)


class WalletService:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        ledger_service: LedgerService,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        asset_repository: AssetRepository,
        paycrest_service: PaycrestService,
        transaction_usecase: TransactionUsecase,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.provider = provider

        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.asset_repository = asset_repository
        self.paycrest_service = paycrest_service
        self.transaction_usecase = transaction_usecase

        self.ledger_service = ledger_service

        self._manager: Optional[WalletManager] = None
        self._manager_id: Optional[str] = None

    #
    # def new_address_manager(self, address_id: str):
    #     self._manager_id = address_id
    #     self._manager = AddressManager(
    #         self.blockrader_config, self._manager, address_id
    #     )
    #     return self

    def new_manager(
        self, wallet_id: str, ledger: Ledger
    ) -> Tuple[Optional["WalletManagerUsecase"], Error]:
        wallet_config = next(
            (w for w in self.blockrader_config.wallets if w.wallet_id == wallet_id),
            None,
        )
        if not wallet_config:
            logger.error(
                "BlockRader WalletConfig not found for wallet_id %s",
                wallet_id,
            )
            return None, error("BlockRader WalletConfig not found")

        self._manager_id = wallet_id
        self._manager = WalletManager(self.blockrader_config, wallet_id)
        manager_usecase = WalletManagerUsecase(
            self, self._manager, wallet_config, ledger
        )
        return manager_usecase, None


class WalletManagerUsecase:
    def __init__(
        self,
        service: WalletService,
        manager: WalletManager,
        wallet_config: WalletConfig,
        ledger_config: Ledger,
    ) -> None:
        self.service = service
        self.manager = manager
        self.wallet_config = wallet_config
        self.ledger_config = ledger_config

    async def _get_user_data(self, user_id: UserId) -> Tuple[Optional[User], Error]:
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
        self, user_id: UserId
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
            chain=self.wallet_config.chain,
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
    ) -> Optional[Error]:
        if (
            not self.service.ledger_service.config.ledgers
            or not self.service.ledger_service.config.ledgers.ledgers
        ):
            return error("Ledger configuration not found")

        # Use stored wallet_config
        wallet_config = self.wallet_config

        # Use stored ledger_config_entry
        ledger_config = self.ledger_config
        ledger_id = ledger_config.ledger_id

        for asset_data in wallet_config.assets:
            if not asset_data.isActive:
                continue

            try:
                asset_type = AssetType(asset_data.symbol.upper())
            except ValueError:
                logger.warning(
                    "Invalid asset symbol found in config: %s. Skipping asset.",
                    asset_data.symbol,
                )
                continue

            balance_request = CreateBalanceRequest(
                ledger_id=ledger_id,
                identity_id=user.ledger_identiy_id,
                currency=asset_data.symbol.lower(),
            )
            (
                ledger_balance,
                err,
            ) = await self.service.ledger_service.balances.create_balance(
                balance_request
            )
            if err:
                logger.error(
                    "Could not create ledger balance for wallet %s, asset %s Error: %s",
                    local_wallet.id,
                    asset_data.symbol,
                    err.message,
                )
                return error(
                    f"Could not create ledger balance for asset {asset_data.symbol}"
                )

            # Create Asset record in local DB
            new_asset = Asset(
                wallet_id=local_wallet.id,
                ledger_balance_id=ledger_balance.balance_id,
                name=asset_data.name,
                asset_id=asset_type,
                address=asset_data.address,
                symbol=asset_data.symbol,
                decimals=asset_data.decimals,
                network=asset_data.network,
                standard=asset_data.standard,
                is_active=asset_data.isActive,
            )
            _, err = await self.service.asset_repository.create_asset(asset=new_asset)
            if err:
                logger.error(
                    "Could not create local asset record for wallet %s, asset %s Error: %s",
                    local_wallet.id,
                    asset_type.value,
                    err.message,
                )
                return error(
                    f"Could not create local asset record for asset {asset_data.symbol}"
                )

        return None

    async def create_user_wallet(self, user_id: UserId) -> Tuple[Optional[Self], Error]:
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

        err = await self._create_ledger_balance(user, wallet)
        if err:
            return None, err

    async def initiate_withdrawal(
        self,
        user: User,
        withdrawal_request: WithdrawalRequest,
        specific_withdrawal: TransferType,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Error]]:
        (
            asset,
            err,
        ) = await self.service.asset_repository.get_asset_by_wallet_id_and_asset_type(  # TODO fucntion name needs mass rename to get_asset_by_wallet_id_and_asset_id
            wallet_id=user.id, asset_type=withdrawal_request.assetId
        )
        if err:
            logger.error(
                "Could not get asset for user %s, asset %s Error: %s",
                user.id,
                withdrawal_request.assetId,
                err.message,
            )
            return None, error("Could not get asset")

        paycrest_rate, err = await self.service.paycrest_service.fetch_letest_usdc_rate(
            amount=float(withdrawal_request.amount),
            currency="NGN",
        )
        if err:
            logger.error(
                "Could not fetch paycrest rate for user %s, amount %s Error: %s",
                user.id,
                withdrawal_request.amount,
                err.message,
            )
            return None, error("Could not fetch paycrest rate")

        network_fee_request = NetworkFeeRequest(
            assetId=withdrawal_request.assetId,
            amount=withdrawal_request.amount,
        )
        blockrader_fee, err = await self.manager.withdraw_network_fee(
            network_fee_request
        )
        if err:
            logger.error(
                "Could not fetch blockrader network fee for user %s, amount %s Error: %s",
                user.id,
                withdrawal_request.amount,
                err.message,
            )
            return None, error("Could not fetch blockrader network fee")

        return {
            "paycrest_rate": paycrest_rate.model_dump(),
            "blockrader_fee": blockrader_fee.model_dump(),
        }, None
