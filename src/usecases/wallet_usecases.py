from typing import Any, Dict, Optional, Self, Tuple
from uuid import UUID, uuid4

from src.dtos import CreateTransactionParams
from src.dtos.wallet_dtos import (BankTransferData, ExternalWalletTransferData,
                                  TransferType, WithdrawalRequest)
from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import (AssetRepository, UserRepository,
                                             WalletRepository)
from src.infrastructure.services import (LedgerService, PaycrestService,
                                         WalletManager)
from src.infrastructure.settings import BlockRaderConfig
from src.models import Asset, User, Wallet
from src.types import (AssetType, Error, IdentiyType, PaymentMethod, Provider,
                       TransactionType, WalletConfig, error, AssetId) # Added AssetId
from src.types.blnk import (CreateBalanceRequest, CreateIdentityRequest,
                            IdentityResponse)
from src.types.blockrader import (CreateAddressRequest, NetworkFeeRequest,
                                  WalletAddressResponse)
from src.types.common_types import UserId
from src.types.ledger_types import Ledger
from src.types.types import WithdrawalMethod # Added this import
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
        logger.debug("Creating new WalletManagerUsecase for wallet ID: %s, ledger: %s", wallet_id, ledger.name)
        wallet_config = next(
            (
                w
                for w in self.blockrader_config.wallets.wallets
                if w.wallet_id == wallet_id
            ),
            None,
        )
        if not wallet_config:
            logger.error(
                "BlockRader WalletConfig not found for wallet_id %s",
                wallet_id,
            )
            return None, error("BlockRader WalletConfig not found")
        logger.debug("Found wallet config for wallet ID: %s", wallet_id)

        self._manager_id = wallet_id
        self._manager = WalletManager(self.blockrader_config, wallet_id)
        manager_usecase = WalletManagerUsecase(
            self, self._manager, wallet_config, ledger
        )
        logger.debug("WalletManagerUsecase created successfully for wallet ID: %s", wallet_id)
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
            phone_number=user.phone_number,
        )
        (
            ledger_identity,
            err,
        ) = await self.ledger_service.identities.create_identity(identity_request)
        if err:
            logger.error(
                "Could not create ledger identity for user %s: %s", user.email,
                err.message,
            )
            return None, error("Could not create ledger identity")
        logger.info("Ledger identity %s created for user %s.", ledger_identity.identity_id, user.email)
        return ledger_identity, None


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
        logger.debug("WalletManagerUsecase initialized for wallet %s, ledger %s", wallet_config.wallet_id, ledger_config.ledger_id)

    async def _get_user_data(self, user_id: UserId) -> Tuple[Optional[User], Error]:
        logger.debug("Attempting to get user data for user ID: %s", user_id)
        user, err = await self.service.user_repository.get_user_by_id(user_id=user_id)
        if err:
            logger.error("Could not get user %s: %s", user_id, err.message)
            return None, error("Could not get user")
        logger.debug("User %s data retrieved.", user_id)
        return user, None

    async def _get_user_wallet(self, user_id: UserId) -> Tuple[Optional[Wallet], Error]:
        logger.debug("Attempting to get user wallet for user ID: %s", user_id)
        # Assuming user has a default wallet, or a way to determine the correct wallet
        wallet, err = await self.service.wallet_repository.get_wallet_by_user_id(
            user_id=user_id
        )
        if err:
            logger.error(
                "Could not get wallet for user %s: %s", user_id, err.message
            )
            return None, error("Could not get user wallet")
        logger.debug("Wallet %s retrieved for user %s.", wallet.id, user_id)
        return wallet, None

    async def _get_asset_by_id(
        self, wallet_id: UUID, asset_id: AssetType
    ) -> Tuple[Optional[Asset], Error]:
        logger.debug("Attempting to get asset %s for wallet %s", asset_id, wallet_id)
        (
            asset,
            err,
        ) = await self.service.asset_repository.get_asset_by_wallet_id_and_asset_type(
            wallet_id=wallet_id, asset_type=asset_id
        )
        if err:
            logger.error(
                "Could not get asset %s for wallet %s: %s",
                asset_id,
                wallet_id,
                err.message,
            )
            return None, error("Could not get asset")
        logger.debug("Asset %s retrieved for wallet %s.", asset.id, wallet_id)
        return asset, None

    async def _generate_provider_wallet(
        self, user_id: UserId
    ) -> Tuple[Optional[WalletAddressResponse], Error]:
        logger.debug("Generating provider wallet for user ID: %s", user_id)
        wallet_request = CreateAddressRequest(
            name="wallet:customer:%s" % user_id,
            metadata={"user_id": str(user_id)},
        )
        provider_wallet, err = await self.manager.generate_address(wallet_request)
        if err:
            logger.error("Could not generate blockrader wallet for user %s: %s", user_id, err.message)
            return None, error("Could not generate wallet")
        logger.info("Provider wallet generated for user %s with address: %s", user_id, provider_wallet.data.address)
        return provider_wallet, None

    async def _create_local_wallet(
        self, user: User, provider_wallet: WalletAddressResponse
    ) -> Tuple[Optional[Wallet], Error]:
        logger.debug("Creating local wallet for user %s with provider wallet ID: %s", user.id, provider_wallet.data.data_id)
        new_wallet = Wallet(
            user_id=user.id,
            address=provider_wallet.data.address,
            chain=self.wallet_config.chain,
            provider=self.service.provider,
            ledger_id=self.ledger_config.ledger_id,
            name="wallet:customer:%s" % user.id,
            derivation_path=provider_wallet.data.derivationPath,
        )

        wallet, err = await self.service.wallet_repository.create_wallet(
            wallet=new_wallet
        )
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
        logger.debug("Creating ledger balances for user %s, local wallet %s", user.id, local_wallet.id)
        wallet_config = self.wallet_config

        # Use stored ledger_config_entry
        ledger_config = self.ledger_config
        ledger_id = ledger_config.ledger_id

        for asset_data in wallet_config.assets:
            logger.debug("Processing asset %s for ledger balance creation.", asset_data.symbol)
            if not asset_data.isActive:
                logger.debug("Asset %s is not active, skipping.", asset_data.symbol)
                continue

            try:
                asset_type = AssetType(asset_data.symbol.lower())
                logger.debug("Asset symbol %s converted to AssetType: %s", asset_data.symbol, asset_type.value)
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
            logger.debug("Creating ledger balance for identity %s, currency %s", user.ledger_identiy_id, asset_data.symbol)
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
                    "Could not create ledger balance for asset %s" % asset_data.symbol
                )
            logger.info("Ledger balance %s created for asset %s in wallet %s.", ledger_balance.balance_id, asset_data.symbol, local_wallet.id)

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
            logger.debug("Creating local asset record for wallet %s, asset %s", local_wallet.id, asset_type.value)
            _, err = await self.service.asset_repository.create_asset(asset=new_asset)
            if err:
                logger.error(
                    "Could not create local asset record for wallet %s, asset %s: %s",
                    local_wallet.id,
                    asset_type.value,
                    err.message,
                )
                return error(
                    "Could not create local asset record for asset %s" % asset_data.symbol
                )
            logger.info("Local asset record %s created for asset %s in wallet %s.", new_asset.id, asset_type.value, local_wallet.id)

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
            rollback_err = await self.service.user_repository.rollback()
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
            logger.error("Failed to create local wallet for user %s: %s", user_id, err.message)
            return None, err
        logger.debug("Local wallet created for user %s", user_id)

        err = await self._create_ledger_balance(user, wallet)
        if err:
            rollback_err = await self.service.user_repository.rollback()
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
        logger.info("Initiating withdrawal for user %s, asset ID: %s, amount: %s", user.id, withdrawal_request.assetId, withdrawal_request.amount)
        # Fetch user's wallet and asset
        user_wallet, err = await self._get_user_wallet(user_id=user.id)
        if err:
            logger.error(
                "Could not get user wallet for user %s: %s", user.id, err.message
            )
            return None, error("Could not get user wallet")
        logger.debug("User wallet %s retrieved for user %s.", user_wallet.id, user.id)

        asset, err = await self._get_asset_by_id(
            wallet_id=user_wallet.id, asset_id=withdrawal_request.assetId
        )
        if err:
            logger.error(
                "Could not get asset %s for user %s, wallet %s: %s",
                withdrawal_request.assetId,
                user.id,
                user_wallet.id,
                err.message,
            )
            return None, error("Could not get asset")
        logger.debug("Asset %s retrieved for user %s.", asset.id, user.id)

        # Determine receiver based on withdrawal type
        receiver_address: str
        payment_method: PaymentMethod
        network: str = ""  # Default network, will be set based on specific withdrawal
        if specific_withdrawal.event == WithdrawalMethod.BANK_TRANSFER:
            bank_transfer_data = BankTransferData.model_validate(
                specific_withdrawal.data
            )
            receiver_address = bank_transfer_data.account_number
            payment_method = PaymentMethod.BANK_TRANSFER
            network = "fiat"  # Assuming fiat for bank transfers
            logger.debug("Withdrawal method: Bank Transfer to %s", receiver_address)
        elif specific_withdrawal.event == WithdrawalMethod.EXTERNAL_WALLET:
            external_wallet_data = ExternalWalletTransferData.model_validate(
                specific_withdrawal.data
            )
            receiver_address = external_wallet_data.address
            payment_method = PaymentMethod.EXTERNAL_WALLET
            network = external_wallet_data.chain.value  # Using chain as network
            logger.debug("Withdrawal method: External Wallet to %s on network %s", receiver_address, network)
        else:
            logger.error("Unsupported withdrawal method: %s for user %s", specific_withdrawal.event, user.id)
            return None, error(
                "Unsupported withdrawal method: %s" % specific_withdrawal.event
            )

        # Create transaction record
        transaction_params = CreateTransactionParams(
            wallet_id=user_wallet.id,
            asset_id=asset.id,
            transaction_type=TransactionType.WITHDRAWAL,
            method=payment_method,
            currency=withdrawal_request.assetId.value.lower(),
            sender=str(user.id),  # Sender is the user's ID
            receiver=receiver_address,
            amount=withdrawal_request.amount,
            status="pending",  # Initial status
            transaction_hash="pending",  # Placeholder, will be updated later
            provider_id=str(uuid4()),  # Unique ID for this transaction attempt
            network=network,
            confirmations=0,
            confirmed=False,
            reference=str(uuid4()),  # Unique reference for the transaction
            note=withdrawal_request.narration,
            chain_id=None,  # To be determined
            reason=None,
            fee=None,  # Will be calculated by blockrader, update transaction later
        )
        logger.debug("Creating transaction record with params: %s", transaction_params.model_dump())
        err = await self.service.transaction_usecase.create_transaction(
            transaction_params
        )
        if err:
            logger.error(
                "Failed to create transaction record for withdrawal for user %s: %s",
                user.id,
                err.message,
            )
            return None, error("Failed to create withdrawal transaction record")
        logger.info("Transaction record %s created for withdrawal for user %s", transaction_params.id, user.id)

        # Now fetch rates and fees, these might be updated in the transaction later
        logger.debug("Fetching paycrest rate for user %s, amount %s", user.id, withdrawal_request.amount)
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
                transaction_id=transaction_params.id,
                new_status="failed",
                message="Failed to fetch paycrest rate: %s" % err.message,
            )
            return None, error("Could not fetch paycrest rate")
        logger.debug("Paycrest rate fetched: %s", paycrest_rate.data)

        network_fee_request = NetworkFeeRequest(
            assetId=withdrawal_request.assetId,
            amount=withdrawal_request.amount,
        )
        logger.debug("Fetching blockrader network fee with request: %s", network_fee_request.model_dump())
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
                transaction_id=transaction_params.id,
                new_status="failed",
                message="Failed to fetch blockrader network fee: %s" % err.message,
            )
            return None, error("Could not fetch blockrader network fee")
        logger.debug("Blockrader network fee fetched: %s", blockrader_fee.fee)

        # Update fee in the transaction
        if blockrader_fee and blockrader_fee.fee:
            logger.debug("Updating transaction %s with fee: %s", transaction_params.id, blockrader_fee.fee)
            update_err = await self.service.transaction_usecase.update_transaction_fee(
                transaction_id=transaction_params.id, fee=blockrader_fee.fee
            )
            if update_err:
                logger.warning(
                    "Failed to update transaction fee for transaction %s: %s",
                    transaction_params.id,
                    update_err.message,
                )
            else:
                logger.info("Transaction %s fee updated to %s.", transaction_params.id, blockrader_fee.fee)

        return {
            "transaction_id": transaction_params.id,
            "paycrest_rate": paycrest_rate.model_dump(),
            "blockrader_fee": blockrader_fee.model_dump(),
        }, None

    async def execute_withdrawal_processing(
        self,
        user_id: UserId,
        pin: str,
        transaction_id: str,
    ) -> Optional[Error]:
        logger.info("Executing withdrawal processing for user %s, transaction %s", user_id, transaction_id)
        transaction, err = await self.service.transaction_usecase.get_transaction_by_id(
            transaction_id=transaction_id
        )
        if err:
            logger.error(
                "Failed to retrieve transaction %s for withdrawal processing: %s",
                transaction_id,
                err.message,
            )
            return error("Failed to retrieve transaction: %s" % err.message)
        logger.debug("Transaction %s retrieved for processing.", transaction_id)

        # 1. Retrieve User
        user, err = await self._get_user_data(user_id)
        if err:
            logger.error(
                "Failed to retrieve user %s for withdrawal processing: %s",
                user_id,
                err.message,
            )
            return error("Failed to retrieve user: %s" % err.message)
        logger.debug("User %s data retrieved for withdrawal processing.", user_id)

        if not await self.service.user_repository.verify_user_pin(
            user_id=user.id, pin=pin
        ):
            logger.error(
                "Invalid PIN for user %s during withdrawal processing for transaction %s", user_id, transaction_id
            )
            # TODO move the pin verificaition out of here
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction_id,
                new_status="failed",
                message="Invalid PIN",
            )
            return error("Invalid PIN")
        logger.debug("PIN verified for user %s.", user_id)

        # 3. Extract Withdrawal Details from Transaction
        # Assuming transaction fields map directly or can be reconstructed
        # from the stored transaction details.
        # For assetId, we convert from UUID stored in transaction.asset_id to AssetId enum
        try:
            asset_id_enum = AssetId(str(transaction.asset_id))
            logger.debug("Asset ID %s from transaction converted to enum: %s", transaction.asset_id, asset_id_enum.value)
        except ValueError:
            logger.error(
                "Invalid Asset ID in transaction %s: %s",
                transaction_id,
                transaction.asset_id,
            )
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction_id,
                new_status="failed",
                message="Invalid asset ID in transaction",
            )
            return error("Invalid asset ID in transaction")

        # 4. Perform Ledger Debit
        logger.debug("Performing ledger debit for user %s, transaction %s, amount %s %s", user_id, transaction_id, transaction.amount, transaction.currency.value)
        debit_result, err = await self.service.ledger_service.balances.debit_balance(
            identity_id=user.ledger_identiy_id,
            currency=transaction.currency.value.lower(),
            amount=transaction.amount,
            # Pass other necessary details from transaction like reference, etc.
            reference=str(transaction.id),  # Use transaction ID as reference
            narration=transaction.note,  # Assuming note can be used for narration
        )
        if err:
            logger.error(
                "Failed to debit ledger for user %s, transaction %s: %s",
                user_id,
                transaction_id,
                err.message,
            )
            await self.service.transaction_usecase.update_transaction_status(
                transaction_id=transaction_id,
                new_status="failed",
                message="Ledger debit failed: %s" % err.message,
            )
            return error("Ledger debit failed: %s" % err.message)
        logger.info("Ledger debited for user %s, transaction %s. Debit result: %s", user_id, transaction_id, debit_result)

        # 5. Update Transaction Status to completed
        logger.debug("Updating transaction %s status to 'completed'", transaction_id)
        err = await self.service.transaction_usecase.update_transaction_status(
            transaction_id=transaction_id,
            new_status="completed",
            message="Withdrawal processed successfully",
        )
        if err:
            logger.error(
                "Failed to update transaction status to completed for transaction %s: %s",
                transaction_id,
                err.message,
            )
            return error("Failed to update transaction status: %s" % err.message)

        logger.info(
            "Withdrawal for user %s, transaction %s processed successfully",
            user_id,
            transaction_id,
        )
        return None
