from decimal import Decimal
from typing import Any, Dict, Optional, Self, Tuple
from uuid import UUID

from src.dtos.transaction_dtos import (
    BankTransferParams,
    CreateTransactionParams,
    CryptoTransactionParams,
)
from src.dtos import AssetBalance, WalletWithAssets
from src.dtos.wallet_dtos import (
    BankTransferData,
    ExternalWalletTransferData,
    TransferType,
    WithdrawalRequest,
)
from src.infrastructure.config_settings import Config
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (
    AssetRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, PaycrestService, WalletManager
from src.infrastructure.settings import BlockRaderConfig
from src.models import Asset, Transaction, User, Wallet
from src.types import (
    AssetType,
    Error,
    IdentiyType,
    PaymentMethod,
    Provider,
    TransactionStatus,
    TransactionType,
    WorldLedger,
    error,
)
from src.types import types
from datetime import datetime, timedelta

from src.types.blnk import CreateBalanceRequest, CreateIdentityRequest, IdentityResponse, RecordTransactionRequest
from src.types.blnk.dtos import UpdateInflightTransactionRequest
from src.types.blockrader import (
    CreateAddressRequest,
    NetworkFeeRequest,
    WalletAddressResponse,
)
from src.types.common_types import AssetId, UserId
from src.types.ledger_types import Ledger
from src.types.types import WithdrawalMethod
from src.usecases.transaction_usecases import TransactionUsecase
from src.usecases.withdrawal_handlers.registry import WithdrawalHandlerRegistry
from src.utils.country_utils import (
    get_country_code_by_currency,
    get_country_name_by_currency,
)

logger = get_logger(__name__)


class WalletService:
    def __init__(
        self,
        repo: WalletRepository,
        *,
        config: Config,
        blockrader_config: BlockRaderConfig,
        ledger_service: LedgerService,
        user_repository: UserRepository,
        asset_repository: AssetRepository,
        paycrest_service: PaycrestService,
        transaction_usecase: TransactionUsecase,
        provider: Provider = Provider.BLOCKRADER,
    ):
        self.config = config
        self.blockrader_config = blockrader_config
        self.provider = provider

        self.repo = repo
        self._user_repository = user_repository
        self._asset_repository = asset_repository
        self.paycrest_service = paycrest_service
        self.transaction_usecase = transaction_usecase

        self.ledger_service = ledger_service

        self._manager: Optional[WalletManager] = None
        self._manager_id: Optional[str] = None
        logger.debug("WalletService initialized with provider: %s", provider.value)

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
        logger.debug(
            "Creating new WalletManagerUsecase for wallet ID: %s, ledger: %s",
            wallet_id,
            ledger.name,
        )
        wallet_config, err = self.blockrader_config.wallets.get_wallet(
            wallet_id=wallet_id
        )
        if err:
            logger.error(
                "BlockRader WalletConfig not found for wallet_id %s, Error: %s",
                wallet_id,
                err.message,
            )
            return None, error("BlockRader WalletConfig not found")
        logger.debug("Found wallet config for wallet ID: %s", wallet_id)

        self._manager_id = wallet_id
        self._manager = WalletManager(self.blockrader_config, wallet_id)
        manager_usecase = WalletManagerUsecase(
            self, self._manager, wallet_config, ledger
        )
        logger.debug(
            "WalletManagerUsecase created successfully for wallet ID: %s", wallet_id
        )
        return manager_usecase, None

    async def create_ledger_identity(
        self, user: User
    ) -> Tuple[Optional[IdentityResponse], Error]:
        logger.debug("Creating ledger identity for user: %s", user.email)
        identity_request = CreateIdentityRequest(
            identity_type=IdentiyType.INDIVIDUAL,
            first_name=user.first_name,
            last_name=user.last_name,
            email_address=user.email,
            # phone_number=user.phone_number,
        )
        (
            ledger_identity,
            err,
        ) = await self.ledger_service.identities.create_identity(identity_request)
        if err:
            logger.error(
                "Could not create ledger identity for user %s: %s",
                user.email,
                err.message,
            )
            return None, error("Could not create ledger identity")
        logger.info(
            "Ledger identity %s created for user %s.",
            ledger_identity.identity_id,
            user.email,
        )
        return ledger_identity, None

    async def get_wallet_with_assets(
        self, user_id: UserId
    ) -> Tuple[Optional[WalletWithAssets], Error]:
        logger.debug("Fetching wallet with assets for user: %s", user_id)
        wallet, err = await self.repo.get_wallet_by_user_id(user_id=user_id.clean())
        if not wallet:
            logger.warning("Wallet not found for user: %s", user_id)
            return None, None

        assets, err = await self._asset_repository.get_assets_by_wallet_id(
            wallet_id=wallet.id
        )
        if err:
            logger.error(
                "Error fetching assets for wallet %s: %s", wallet.id, err.message
            )
            assets = []

        asset_balances = []
        for asset in assets:
            balance_data = Decimal("0")

            if asset.ledger_balance_id:
                bal_resp, err = await self.ledger_service.balances.get_balance(
                    asset.ledger_balance_id
                )
                if err:
                    logger.error(
                        "Error fetching balance for asset %s (ledger_id: %s): %s",
                        asset.id,
                        asset.ledger_balance_id,
                        err.message,
                    )
                    continue
                balance_data = Decimal(str(bal_resp.balance)) / 100

            asset_balances.append(
                AssetBalance(
                    asset_id=asset.get_prefixed_id(),
                    name=asset.name,
                    symbol=asset.symbol,
                    decimals=asset.decimals,
                    asset_type=asset.asset_type,
                    balance=balance_data,
                    network=asset.network,
                    address=asset.address,
                    standard=asset.standard,
                    is_active=asset.is_active,
                )
            )

        wallet_with_assets = WalletWithAssets(
            id=wallet.get_prefixed_id(),
            address=wallet.address,
            chain=wallet.chain,
            provider=wallet.provider.name
            if hasattr(wallet.provider, "name")
            else str(wallet.provider),
            is_active=wallet.is_active,
            assets=asset_balances,
        )

        return wallet_with_assets, None

    async def get_asset_balance(
        self, user_id: UserId, asset_id: AssetId
    ) -> Tuple[Optional[AssetBalance], Error]:
        logger.debug(
            "Fetching specific asset balance for user: %s, asset: %s", user_id, asset_id
        )
        wallet, err = await self.repo.get_wallet_by_user_id(user_id=user_id.clean())
        if not wallet:
            logger.warning("Wallet not found for user: %s", user_id)
            return None, error("Wallet not found")

        asset, err = await self._asset_repository.find_one(
            id=asset_id.clean(),
            wallet_id=wallet.id,
        )
        if err:
            logger.warning("Asset %s not found for wallet %s", asset_id, wallet.id)
            return None, error("Asset not found")

        balance_data = Decimal("0")
        if asset.ledger_balance_id:
            bal_resp, err = await self.ledger_service.balances.get_balance(
                asset.ledger_balance_id
            )
            if err:
                logger.error(
                    "Error fetching balance for asset %s (ledger_id: %s): %s",
                    asset.id,
                    asset.ledger_balance_id,
                    err.message,
                )
                return None, error("Error fetching balance")
            balance_data = Decimal(str(bal_resp.balance)) / 100

        asset_balance = AssetBalance(
            asset_id=asset.get_prefixed_id(),
            name=asset.name,
            symbol=asset.symbol,
            decimals=asset.decimals,
            asset_type=asset.asset_type,
            balance=balance_data,
            network=asset.network,
            address=asset.address,
            standard=asset.standard,
            is_active=asset.is_active,
        )

        return asset_balance, None


class WalletManagerUsecase:
    def __init__(
        self,
        service: WalletService,
        manager: WalletManager,
        wallet_config: types.Wallet,
        ledger_config: Ledger,
    ) -> None:
        self.service = service
        self.manager = manager
        self.wallet_config = wallet_config
        self.ledger_config = ledger_config
        logger.debug(
            "WalletManagerUsecase initialized for wallet %s, ledger %s",
            wallet_config.wallet_id,
            ledger_config.ledger_id,
        )

    async def _get_user_data(self, user_id: UserId) -> Tuple[Optional[User], Error]:
        logger.debug("Attempting to get user data for user ID: %s", user_id)
        user, err = await self.service._user_repository.get_user_by_id(user_id=user_id)
        if err:
            logger.error("Could not find user %s: %s", user_id, err.message)
            return None, error("Could not find user")
        logger.debug("User %s data retrieved.", user_id)
        return user, None

    async def _get_user_wallet(self, user_id: UserId) -> Tuple[Optional[Wallet], Error]:
        logger.debug("Attempting to get user wallet for user ID: %s", user_id)
        # Assuming user has a default wallet, or a way to determine the correct wallet
        wallet, err = await self.service.repo.get_wallet_by_user_id(user_id=user_id)
        if err:
            logger.error("Could not find wallet for user %s: %s", user_id, err.message)
            return None, error("Could not find user wallet")
        logger.debug("Wallet %s retrieved for user %s.", wallet.id, user_id)
        return wallet, None

    async def _get_asset_by_id(
        self, wallet_id: UUID, asset_id: UUID
    ) -> Tuple[Optional[Asset], Error]:
        logger.debug("Attempting to get asset %s for wallet %s", asset_id, wallet_id)
        (
            asset,
            err,
        ) = await self.service._asset_repository.find_one(
            wallet_id=wallet_id, id=asset_id
        )
        if err:
            logger.error(
                "Could not find asset %s for wallet %s: %s",
                asset_id,
                wallet_id,
                err.message,
            )
            return None, error("Could not find asset")
        logger.debug("Asset %s retrieved for wallet %s.", asset.id, wallet_id)
        return asset, None

    async def _generate_provider_wallet(
        self, user_id: UserId
    ) -> Tuple[Optional[WalletAddressResponse], Error]:
        logger.debug("Generating provider wallet for user ID: %s", user_id)
        wallet_request = CreateAddressRequest(
            name=f"wallet:customer:{user_id}",
            metadata={"user_id": str(user_id)},
        )
        provider_wallet, err = await self.manager.generate_address(wallet_request)
        if err:
            logger.error(
                "Could not generate blockrader wallet for user %s: %s",
                user_id,
                err.message,
            )
            return None, error("Could not generate wallet")
        logger.info(
            "Provider wallet generated for user %s with address: %s",
            user_id,
            provider_wallet.data.address,
        )
        return provider_wallet, None

    async def _create_local_wallet(
        self, user: User, provider_wallet: WalletAddressResponse
    ) -> Tuple[Optional[Wallet], Error]:
        logger.debug(
            "Creating local wallet for user %s with provider wallet ID: %s",
            user.id,
            provider_wallet.data.data_id,
        )
        new_wallet = Wallet(
            user_id=user.id,
            address=provider_wallet.data.address,
            chain=self.wallet_config.chain,
            provider=self.service.provider,
            ledger_id=self.ledger_config.ledger_id,
            name=f"wallet:customer:{user.id}",
            derivation_path=provider_wallet.data.derivationPath,
        )

        wallet, err = await self.service.repo.create(new_wallet)
        if err:
            logger.error(
                "Could not save wallet %s on provider %s to db: %s",
                provider_wallet.data.data_id,
                self.service.provider.name,
                err.message,
            )
            return None, err
        logger.info("Local wallet %s created for user %s.", wallet.id, user.id)
        return wallet, None

    async def _create_ledger_balance(
        self, user: User, local_wallet: Wallet
    ) -> Optional[Error]:
        logger.debug(
            "Creating ledger balances for user %s, local wallet %s",
            user.id,
            local_wallet.id,
        )
        wallet_config = self.wallet_config

        # Use stored ledger_config_entry
        ledger_config = self.ledger_config
        ledger_id = ledger_config.ledger_id

        for asset_data in wallet_config.assets:
            logger.debug(
                "Processing asset %s for ledger balance creation.", asset_data.symbol
            )
            if not asset_data.isActive:
                logger.debug("Asset %s is not active, skipping.", asset_data.symbol)
                continue

            try:
                asset_type = AssetType(asset_data.symbol.lower())
                logger.debug(
                    "Asset symbol %s converted to AssetType: %s",
                    asset_data.symbol,
                    asset_type.value,
                )
            except ValueError:
                logger.warning(
                    "Invalid asset symbol found in config: %s. Skipping asset.",
                    asset_data.symbol,
                )
                continue

            balance_request = CreateBalanceRequest(
                ledger_id=ledger_id,
                identity_id=user.ledger_identity_id,
                currency=asset_data.symbol.lower(),
            )
            logger.debug(
                "Creating ledger balance for identity %s, currency %s",
                user.ledger_identity_id,
                asset_data.symbol,
            )
            (
                ledger_balance,
                err,
            ) = await self.service.ledger_service.balances.create_balance(
                balance_request
            )
            if err:
                logger.error(
                    "Could not create ledger balance for wallet %s, asset %s: %s",
                    local_wallet.id,
                    asset_data.symbol.upper(),
                    err.message,
                )
                return error(
                    f"Could not create ledger balance for asset {asset_data.symbol}"
                )
            logger.info(
                "Ledger balance %s created for asset %s in wallet %s.",
                ledger_balance.balance_id,
                asset_data.symbol,
                local_wallet.id,
            )

            # Create Asset record in local DB
            new_asset = Asset(
                wallet_id=local_wallet.id,
                ledger_balance_id=ledger_balance.balance_id,
                name=asset_data.name,
                asset_type=asset_type,
                asset_id=asset_data.asset_id,
                address=asset_data.address,
                symbol=asset_data.symbol,
                decimals=asset_data.decimals,
                network=asset_data.network,
                standard=asset_data.standard,
                is_active=asset_data.isActive,
            )
            logger.debug(
                "Creating local asset record for wallet %s, asset %s",
                local_wallet.id,
                asset_type.value,
            )
            _, err = await self.service._asset_repository.create_asset(asset=new_asset)
            if err:
                logger.error(
                    "Could not create local asset record for wallet %s, asset %s: %s",
                    local_wallet.id,
                    asset_type.value,
                    err.message,
                )
                return error(
                    f"Could not create local asset record for asset {asset_data.symbol}"
                )
            logger.info(
                "Local asset record %s created for asset %s in wallet %s.",
                new_asset.id,
                asset_type.value,
                local_wallet.id,
            )

        return None

    async def create_user_wallet(self, user_id: UserId) -> Tuple[Optional[Self], Error]:
        logger.info("Creating user wallet for user ID: %s", user_id)
        user, err = await self._get_user_data(user_id)
        if err:
            return None, err
        logger.debug("User data retrieved for user %s", user_id)

        provider_wallet, err = await self._generate_provider_wallet(
            user.get_prefixed_id()
        )
        if err:
            rollback_err = await self.service._user_repository.rollback()
            if rollback_err:
                logger.error(
                    "Failed to rollback user creation for user %s after provider wallet failure: %s",
                    user_id,
                    rollback_err.message,
                    exc_info=True,
                )
            return None, err
        logger.debug("Provider wallet generated for user %s", user_id)

        wallet, err = await self._create_local_wallet(user, provider_wallet)
        if err:
            logger.error(
                "Failed to create local wallet for user %s: %s", user_id, err.message
            )
            return None, err
        logger.debug("Local wallet created for user %s", user_id)

        err = await self._create_ledger_balance(user, wallet)
        if err:
            rollback_err = await self.service._user_repository.rollback()
            if rollback_err:
                logger.error(
                    "Failed to rollback user creation for user %s after ledger balance failure: %s",
                    user_id,
                    rollback_err.message,
                    exc_info=True,
                )
            return None, err
        logger.info("User wallet created successfully for user %s", user_id)
        return self, None

    async def initiate_withdrawal(
        self,
        user: User,
        withdrawal_request: WithdrawalRequest,
        specific_withdrawal: TransferType,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Error]]:
        logger.info(
            "Initiating withdrawal for user %s, asset ID: %s, amount: %s",
            user.id,
            withdrawal_request.asset_id,
            withdrawal_request.amount,
        )

        withdrawal_method = specific_withdrawal.event
        withdrawal_handler = WithdrawalHandlerRegistry.get_handler(withdrawal_method)

        if not withdrawal_handler:
            logger.error(
                "Unsupported withdrawal method: %s for user %s",
                withdrawal_method,
                user.id,
            )
            return None, error(f"Unsupported withdrawal method: {withdrawal_method}")

        # Fetch user's wallet and asset
        user_wallet, err = await self._get_user_wallet(user_id=user.id)
        if err:
            logger.error(
                "Could not find user wallet for user %s: %s", user.id, err.message
            )
            return None, error("Could not find user wallet")
        logger.debug("User wallet %s retrieved for user %s.", user_wallet.id, user.id)

        asset, err = await self._get_asset_by_id(
            wallet_id=user_wallet.id, asset_id=withdrawal_request.asset_id.clean()
        )
        if err:
            logger.error(
                "Could not find asset %s for user %s, wallet %s: %s",
                withdrawal_request.asset_id,
                user.id,
                user_wallet.id,
                err.message,
            )
            return None, error("Could not find asset")
        logger.debug("Asset %s retrieved for user %s.", asset.id, user.id)

        # Map WithdrawalMethod to PaymentMethod
        payment_method = PaymentMethod.BLOCKCHAIN
        if withdrawal_method == WithdrawalMethod.BANK_TRANSFER:
            payment_method = PaymentMethod.BANK_TRANSFER

        specific_data: BankTransferData | ExternalWalletTransferData
        if withdrawal_method == WithdrawalMethod.BANK_TRANSFER:
            specific_data = BankTransferData.model_validate(specific_withdrawal.data)
        elif withdrawal_method == WithdrawalMethod.EXTERNAL_WALLET:
            specific_data = ExternalWalletTransferData.model_validate(
                specific_withdrawal.data
            )
        else:
            return None, error(
                f"Invalid specific withdrawal data for method: {withdrawal_method}"
            )

        common_transaction_params: CreateTransactionParams

        base_kwargs = {
            "wallet_id": user_wallet.id,
            "asset_id": asset.id,
            "transaction_type": TransactionType.DEBIT,
            "payment_type": TransactionType.DEBIT,
            "method": payment_method,
            "currency": withdrawal_request.currency,
            "sender": user.get_prefixed_id(),
            "receiver": "N/A",
            "amount": withdrawal_request.amount,
            "narration": withdrawal_request.narration,
            "fee": None,
            "country": get_country_name_by_currency(
                self.service.config.countries,
                withdrawal_request.currency,
            ),
        }

        if withdrawal_method == WithdrawalMethod.BANK_TRANSFER:
            # For Bank Transfer, create BankTransferParams
            if isinstance(specific_data, BankTransferData):
                country_code = get_country_code_by_currency(
                    self.service.config.countries, withdrawal_request.currency
                )
                if not country_code:
                    logger.warning(
                        "Could not determine country code for currency %s",
                        withdrawal_request.currency,
                    )
                    bank_name = "Unknown Bank"
                else:
                    found_banks = self.service.config.banks_data.get(
                        country_code=country_code, code=specific_data.bank_code
                    )
                    bank_name = found_banks[0].name if found_banks else "Unknown Bank"

                common_transaction_params = BankTransferParams(
                    **base_kwargs,
                    bank_code=specific_data.bank_code,
                    bank_name=bank_name,
                    account_number=specific_data.account_number,
                    account_name=specific_data.account_name,
                    provider="paycrest",
                )
            else:
                return None, error("Invalid data for bank transfer")

        else:
            # Default to Crypto params (External Wallet)
            common_transaction_params = CryptoTransactionParams(
                **base_kwargs,
                status=TransactionStatus.PENDING,
                transaction_hash="pending",
                network="N/A",
                chain_id=None,
            )

        # Call the specific handler
        transaction, err = await withdrawal_handler(
            wallet_manager=self,
            user=user,
            withdrawal_request=withdrawal_request,
            transfer_data=specific_data,
            create_transaction_params=common_transaction_params,
        )
        if err:
            logger.error(
                "Handler failed for withdrawal method %s for user %s: %s",
                withdrawal_method,
                user.id,
                err.message,
            )
            return None, err
        logger.info(
            "Transaction record %s created by handler for withdrawal for user %s",
            transaction.id,
            user.id,
        )

        # Create in-flight transaction on the ledger
        logger.debug(
            "Creating in-flight ledger transaction for withdrawal %s", transaction.id
        )
        ledger_txn_request = RecordTransactionRequest(
            amount=int(withdrawal_request.amount * 100),  
            currency=withdrawal_request.currency.value.lower(),
            source=asset.ledger_balance_id,
            destination=WorldLedger.WORLD_OUT,
            description=f"In-flight withdrawal for {user.id} to {withdrawal_method.value}",
            reference=transaction.reference,
            inflight=True,
            expires_at=datetime.now() + timedelta(hours=24),  
        )
        ledger_inflight_txn, err = (
            await self.service.ledger_service.transactions.record_transaction(
                ledger_txn_request
            )
        )
        if err:
            logger.error(
                "Failed to create in-flight ledger transaction for withdrawal %s: %s",
                transaction.id,
                err.message,
            )
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction.id,
                new_status=TransactionStatus.FAILED,
                error_message=f"Failed to create in-flight ledger transaction: {err.message}",
            )
            return None, error("Failed to create in-flight ledger transaction")

        transaction.ledger_transaction_id = ledger_inflight_txn.transaction_id
        _, err = await self.service.transaction_usecase.repo.update(transaction)
        if err:
            logger.error(
                "Failed to update local transaction %s with ledger transaction ID %s: %s",
                transaction.id,
                ledger_inflight_txn.transaction_id,
                err.message,
            )
            logger.error(
                "Attempting to void in-flight ledger transaction %s due to local transaction update failure",
                ledger_inflight_txn.transaction_id,
            )
            void_req = UpdateInflightTransactionRequest(status="void")
            void_err = await self.service.ledger_service.transactions.update_inflight_transaction(
                ledger_inflight_txn.transaction_id, void_req
            )
            if void_err:
                logger.critical(
                    "Failed to void in-flight ledger transaction %s after local transaction update failure: %s",
                    ledger_inflight_txn.transaction_id,
                    void_err.message,
                )
            return None, error("Failed to update local transaction with ledger ID")
        logger.info(
            "In-flight ledger transaction %s created and linked to local transaction %s",
            ledger_inflight_txn.transaction_id,
            transaction.id,
        )


        logger.debug(
            "Fetching paycrest rate for user %s, amount %s",
            user.id,
            withdrawal_request.amount,
        )
        paycrest_rate, err = await self.service.paycrest_service.fetch_letest_usdc_rate(
            amount=float(withdrawal_request.amount),
            currency="NGN",
        )
        if err:
            logger.error(
                "Could not fetch paycrest rate for user %s, amount %s: %s",
                user.id,
                withdrawal_request.amount,
                err.message,
            )
            # Update transaction status to failed due to rate fetch error
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction.id,
                new_status=TransactionStatus.FAILED,
                error_message=f"Failed to fetch paycrest rate: {err.message}",
            )
            # Cancel in-flight ledger transaction
            logger.error(
                "Attempting to void in-flight ledger transaction %s due to paycrest rate fetch failure",
                transaction.ledger_transaction_id,
            )
            void_req = UpdateInflightTransactionRequest(status="void")
            void_err = await self.service.ledger_service.transactions.update_inflight_transaction(
                transaction.ledger_transaction_id, void_req
            )
            if void_err:
                logger.critical(
                    "Failed to void in-flight ledger transaction %s after paycrest rate fetch failure: %s",
                    transaction.ledger_transaction_id,
                    void_err.message,
                )
            return None, error("Could not fetch paycrest rate")
        if hasattr(paycrest_rate, "data"):
            logger.debug("Paycrest rate fetched: %s", paycrest_rate.data)
        else:
            logger.debug("Paycrest rate fetched: %s", paycrest_rate)

        blockrader_asset, err = self.wallet_config.get(asset_id=str(asset.asset_id))
        if err:
            logger.error(
                "Could not fetch blockrader network fee for user %s, amount %s: %s",
                user.id,
                withdrawal_request.amount,
                err.message,
            )
            return None, error("Could not fetch blockrader network fee")
        network_fee_request = NetworkFeeRequest(
            assetId=blockrader_asset.blockrader_asset_id,
            amount=str(withdrawal_request.amount),
            address=user_wallet.address,
        )
        logger.debug(
            "Fetching blockrader network fee with request: %s",
            network_fee_request.model_dump(),
        )
        blockrader_fee, err = await self.manager.withdraw_network_fee(
            network_fee_request
        )
        if err:
            logger.error(
                "Could not fetch blockrader network fee for user %s, amount %s: %s",
                user.id,
                withdrawal_request.amount,
                err.message,
            )
            # Update transaction status to failed due to network fee fetch error
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction.id,
                new_status=TransactionStatus.FAILED,
                error_message=err.message,
            )
            return None, error("Could not fetch blockrader network fee")
        logger.debug(
            "Blockrader network fee fetched: %s", blockrader_fee.data.networkFee
        )

        # Update fee in the transaction
        if blockrader_fee and blockrader_fee.data.networkFee:
            logger.debug(
                "Updating transaction %s with fee: %s",
                transaction.id,
                blockrader_fee.data.networkFee,
            )
            update_err = await self.service.transaction_usecase.update_transaction_fee(
                transaction_id=transaction.id, fee=blockrader_fee.data.networkFee
            )
            if update_err:
                logger.warning(
                    "Failed to update transaction fee for transaction %s: %s",
                    transaction.id,
                    update_err.message,
                )
            else:
                logger.info(
                    "Transaction %s fee updated to %s.",
                    transaction.id,
                    blockrader_fee.data.networkFee,
                )

        return {
            "transaction_id": transaction.get_prefixed_id(),
            "paycrest_rate": paycrest_rate.model_dump(),
            "blockrader_fee": blockrader_fee.model_dump(),
        }, None

    async def _retrieve_withdrawal_transaction_and_user(
        self, user_id: UserId, transaction_id: str
    ) -> Tuple[Optional[Tuple[Transaction, User]], Optional[Error]]:
        logger.debug(
            "Retrieving transaction %s and user %s for withdrawal processing",
            transaction_id,
            user_id,
        )
        transaction, err = await self.service.transaction_usecase.get_transaction_by_id(
            transaction_id=transaction_id
        )
        if err:
            logger.error(
                "Failed to retrieve transaction %s for withdrawal processing: %s",
                transaction_id,
                err.message,
            )
            return None, error(f"Failed to retrieve transaction: {err.message}")

        user, err = await self._get_user_data(user_id)
        if err:
            logger.error(
                "Failed to retrieve user %s for withdrawal processing: %s",
                user_id,
                err.message,
            )
            return None, error(f"Failed to retrieve user: {err.message}")
        logger.debug(
            "Transaction %s and user %s retrieved for processing.",
            transaction_id,
            user_id,
        )
        return (transaction, user), None

    async def _update_withdrawal_transaction_status(
        self, transaction_id: str, new_status: TransactionStatus
    ) -> Optional[Error]:
        logger.debug(
            "Updating transaction %s status to '%s'", transaction_id, new_status.value
        )
        err = await self.service.transaction_usecase.update_transaction_status(
            transaction_id=transaction_id,
            new_status=new_status.value,
        )
        if err:
            logger.error(
                "Failed to update transaction status to %s for transaction %s: %s",
                new_status.value,
                transaction_id,
                err.message,
            )
            return error(f"Failed to update transaction status: {err.message}")
        logger.info(
            "Transaction %s status updated to %s.", transaction_id, new_status.value
        )
        return None

    async def process_withdrawal_execution(
        self,
        user_id: UserId,
        transaction_id: str,
    ) -> Optional[Error]:
        logger.info(
            "Processing withdrawal execution for user %s, transaction %s",
            user_id,
            transaction_id,
        )

        data, err = await self._retrieve_withdrawal_transaction_and_user(
            user_id, transaction_id
        )
        if err:
            return err
        transaction, user = data

        if not transaction.ledger_transaction_id:
            logger.error(
                "Cannot process withdrawal execution for transaction %s without a ledger transaction ID",
                transaction.id,
            )
            return error("Missing ledger transaction ID for withdrawal")

        logger.info(
            "Committing in-flight ledger transaction %s for withdrawal %s",
            transaction.ledger_transaction_id,
            transaction.id,
        )
        update_req = UpdateInflightTransactionRequest(status="commit")
        _, err = await self.service.ledger_service.transactions.update_inflight_transaction(
            transaction.ledger_transaction_id, update_req
        )
        if err:
            logger.error(
                "Failed to commit in-flight ledger transaction %s for withdrawal %s: %s",
                transaction.ledger_transaction_id,
                transaction.id,
                err.message,
            )
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction.id,
                new_status=TransactionStatus.FAILED,
                error_message=err.message,
            )
            return None, error("Could not fetch blockrader network fee")
            return error("Failed to commit in-flight ledger transaction")

        logger.info(
            "Successfully committed in-flight ledger transaction %s for withdrawal %s",
            transaction.ledger_transaction_id,
            transaction.id,
        )

        err = await self._update_withdrawal_transaction_status(
            transaction_id,
            TransactionStatus.COMPLETED,
        )
        if err:
            return err

        logger.info(
            "Withdrawal for user %s, transaction %s processed successfully",
            user_id,
            transaction_id,
        )
        return None
