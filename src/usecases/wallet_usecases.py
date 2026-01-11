from typing import Optional, Self, Tuple

from src.dtos.transaction_dtos import CreateTransactionParams
from src.dtos.wallet_dtos import (BankTransferData, ExternalWalletTransferData,
                                  TransferType, WithdrawalRequest)
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (AssetRepository, UserRepository,
                                             WalletRepository)
from src.infrastructure.services import (LedgerService, PaystackService,
                                         WalletManager)
from src.infrastructure.settings import BlockRaderConfig, LedgderServiceConfig
from src.models import Asset, User, Wallet
from src.types import (AssetType, Error, IdentiyType, Provider, WalletConfig,
                       error)
from src.types.blnk import (CreateBalanceRequest, CreateIdentityRequest,
                            IdentityResponse, RecordTransactionRequest)
from src.types.blockrader import CreateAddressRequest, WalletAddressResponse
from src.types.common_types import UserId, WorldLedger
from src.types.ledger_types import Ledger
from src.types.types import TransactionType, WithdrawalMethod
from src.usecases.transaction_usecases import TransactionUsecase

logger = get_logger(__name__)


class WalletService:
    def __init__(
        self,
        blockrader_config: BlockRaderConfig,
        ledger_service_config: LedgderServiceConfig,
        user_repository: UserRepository,
        wallet_repository: WalletRepository,
        asset_repository: AssetRepository,
        paystack_service: PaystackService,
        transaction_usecase: TransactionUsecase,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.blockrader_config = blockrader_config
        self.ledger_service_config = ledger_service_config
        self.provider = provider

        self.user_repository = user_repository
        self.wallet_repository = wallet_repository
        self.asset_repository = asset_repository
        self.paystack_service = paystack_service
        self.transaction_usecase = transaction_usecase

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

    def new_manager(
        self, wallet_id: str, ledger: Ledger
    ) -> Tuple[Optional["WalletManagerUsecase"], Error]:
        wallet_config = next(
            (w for w in self.blockrader_config.wallets if w.wallet_id == wallet_id),
            None,
        )
        if not wallet_config:
            logger.error(
                "BlockRader WalletConfig not found for wallet_id %s and chain %s",
                wallet_id,
                wallet_config.chain,
            )
            return None, error("BlockRader WalletConfig not found")

        self._manager_id = wallet_id
        self._manager = WalletManager(self.blockrader_config, wallet_id)
        manager_usecase = WalletManagerUsecase(
            self, self._manager, wallet_config, ledger
        )
        return manager_usecase, None


class WalletManagerUsecase():
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
    ) -> Optional[Error]:
        (
            asset,
            err,
        ) = await self.service.asset_repository.get_asset_by_wallet_id_and_asset_type(
            wallet_id=user.id, asset_type=withdrawal_request.assetId
        )
        if err:
            logger.error(
                "Could not get asset for user %s, asset %s Error: %s",
                user.id,
                withdrawal_request.assetId,
                err.message,
            )
            return error("Could not get asset")

        match specific_withdrawal.event:
            case WithdrawalMethod.BANK_TRANSFER:
                bank_transfer_data = BankTransferData.model_validate(
                    specific_withdrawal.data
                )
                return await self._handle_bank_transfer(
                    user, withdrawal_request, bank_transfer_data, asset
                )
            case WithdrawalMethod.EXTERNAL_WALLET:
                external_wallet_transfer_data = (
                    ExternalWalletTransferData.model_validate(specific_withdrawal.data)
                )
                return await self._handle_external_wallet_transfer(
                    user, withdrawal_request, external_wallet_transfer_data, asset
                )
            case _:
                return error("Unsupported withdrawal method")

    async def _handle_bank_transfer(
        self,
        user: User,
        withdrawal_request: WithdrawalRequest,
        bank_transfer_data: BankTransferData,
        asset: Asset,
    ) -> Optional[Error]:
        # Initiate Paystack transfer
        transfer_code, err = await self.service.paystack_service.initiate_transfer(
            amount=withdrawal_request.amount,
            recipient_bank_code=bank_transfer_data.bank_code,
            recipient_account_number=bank_transfer_data.account_number,
            recipient_name=bank_transfer_data.account_name,
            narration=withdrawal_request.narration,
        )
        if err:
            logger.error(
                "Paystack transfer initiation failed for user %s: %s",
                user.id,
                err.message,
            )
            return error("Bank transfer failed")

        # Record transaction in local DB
        create_transaction_params = CreateTransactionParams(
            wallet_id=asset.wallet_id,
            transaction_type=TransactionType.DEBIT,
            method=WithdrawalMethod.BANK_TRANSFER,
            currency=asset.symbol,
            sender=user.id,  # This could be the user's wallet address or similar
            receiver=bank_transfer_data.account_number,
            amount=withdrawal_request.amount,
            status="pending",  # Initial status
            transaction_hash=transfer_code,  # Paystack transfer code as hash
            provider_id=transfer_code,  # Paystack transfer code as provider ID
            network="N/A",  # Not applicable for bank transfer
            confirmations=0,  # Not applicable
            confirmed=False,  # Not confirmed initially
            reference=withdrawal_request.narration,
            note=f"Bank transfer to {bank_transfer_data.account_name}",
        )
        _, err = await self.service.transaction_usecase.create_transaction(
            create_transaction_params
        )
        if err:
            logger.error(
                "Failed to record local transaction for user %s: %s",
                user.id,
                err.message,
            )
            return error("Failed to record transaction")

        # Record transaction in ledger
        transaction_request = RecordTransactionRequest(
            amount=int(withdrawal_request.amount * 100),  # Convert to minor units
            reference=transfer_code,
            source=asset.ledger_balance_id,
            destination=WorldLedger.WORLD,  # To external world
            description=withdrawal_request.narration,
        )
        _, err = await self.service.ledger_service.transactions.record_transaction(
            transaction_request
        )
        if err:
            logger.error(
                "Failed to record ledger transaction for user %s: %s",
                user.id,
                err.message,
            )
            return error("Failed to record ledger transaction")

        return None

    async def _handle_external_wallet_transfer(
        self,
        user: User,
        withdrawal_request: WithdrawalRequest,
        external_wallet_transfer_data: ExternalWalletTransferData,
        asset: Asset,
    ) -> Optional[Error]:
        # Initiate external wallet transfer using self.manager
        # This part requires more details about blockrader's transfer API
        # For now, it's a placeholder
        logger.info(
            "Initiating external wallet transfer for user %s to %s with asset %s amount %s",
            user.id,
            external_wallet_transfer_data.address,
            withdrawal_request.assetId,
            withdrawal_request.amount,
        )
        # Placeholder for actual transfer logic
        # For example:
        # transfer_response, err = await self.manager.transfer_asset(
        #     source_asset_id=asset.asset_id,
        #     destination_address=external_wallet_transfer_data.address,
        #     amount=withdrawal_request.amount,
        #     chain=external_wallet_transfer_data.chain,
        # )
        # if err:
        #     logger.error("External wallet transfer failed for user %s: %s", user.id, err.message)
        #     return error("External wallet transfer failed")

        # Record transaction in local DB and ledger (similar to bank transfer)
        # Placeholder
        return error("External wallet transfer not fully implemented")
