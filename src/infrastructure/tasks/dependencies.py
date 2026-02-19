import functools

from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.db import get_session
from src.infrastructure.repositories import (
    AssetRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, PaycrestService, WalletManager
from src.usecases import TransactionUsecase, WalletManagerUsecase, WalletService


class TaskDependenciesFactory:
    def __init__(self, session: AsyncSession, ledger_config, paycrest_config, blockrader_config):
        self.session = session
        self.ledger_config = ledger_config
        self.paycrest_config = paycrest_config
        self.blockrader_config = blockrader_config

    @functools.cached_property
    def user_repository(self) -> UserRepository:
        return UserRepository(self.session)

    @functools.cached_property
    def wallet_repository(self) -> WalletRepository:
        return WalletRepository(self.session)

    @functools.cached_property
    def asset_repository(self) -> AssetRepository:
        return AssetRepository(self.session)

    @functools.cached_property
    def ledger_service(self) -> LedgerService:
        return LedgerService(self.ledger_config)

    @functools.cached_property
    def paycrest_service(self) -> PaycrestService:
        return PaycrestService(self.paycrest_config)

    @functools.cached_property
    def transaction_usecase(self) -> TransactionUsecase:
        return TransactionUsecase(
            user_repository=self.user_repository,
            wallet_repository=self.wallet_repository,
            asset_repository=self.asset_repository,
            ledger_service=self.ledger_service,
        )

    @functools.cached_property
    def wallet_service(self) -> WalletService:
        return WalletService(
            self.wallet_repository,
            blockrader_config=self.blockrader_config,
            ledger_service=self.ledger_service,
            user_repository=self.user_repository,
            asset_repository=self.asset_repository,
            paycrest_service=self.paycrest_service,
            transaction_usecase=self.transaction_usecase,
        )

    def get_wallet_manager_usecase(
        self, wallet_name: str, ledger_id: str
    ) -> WalletManagerUsecase:
        wallet_config, err = self.blockrader_config.wallets.get_wallet(wallet_name)
        if err or not wallet_config:
            raise ValueError(f"WalletConfig not found for wallet_name {wallet_name}")

        # Find ledger_config from config
        ledger_config = next(
            (
                ledger_item
                for ledger_item in self.ledger_config.ledgers
                if ledger_item.ledger_id == ledger_id
            ),
            None,
        )
        if not ledger_config:
            raise ValueError(f"LedgerConfig not found for ledger_id {ledger_id}")

        manager = WalletManager(self.blockrader_config, wallet_config.wallet_id)

        return WalletManagerUsecase(
            service=self.wallet_service,
            manager=manager,
            wallet_config=wallet_config,
            ledger_config=ledger_config,
        )


# Helper function to be used by tasks
def get_task_wallet_manager_usecase(
    ledger_config, paycrest_config, blockrader_config, wallet_name: str, ledger_id: str
) -> WalletManagerUsecase:
    session = get_session()
    factory = TaskDependenciesFactory(session, ledger_config, paycrest_config, blockrader_config)
    return factory.get_wallet_manager_usecase(wallet_name, ledger_id)