import functools

from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.config_settings import Config
from src.infrastructure.db import get_session
from src.infrastructure.repositories import (
    AssetRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, PaycrestService, WalletManager
from src.usecases import TransactionUsecase, WalletManagerUsecase, WalletService


class TaskDependenciesFactory:
    def __init__(self, session: AsyncSession, config: Config):
        self.session = session
        self.config = config

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
        return LedgerService(self.config.ledger)

    @functools.cached_property
    def paycrest_service(self) -> PaycrestService:
        return PaycrestService(self.config.paycrest)

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
            blockrader_config=self.config.block_rader,
            ledger_service=self.ledger_service,
            user_repository=self.user_repository,
            wallet_repository=self.wallet_repository,
            asset_repository=self.asset_repository,
            paycrest_service=self.paycrest_service,
            transaction_usecase=self.transaction_usecase,
        )

    def get_wallet_manager_usecase(
        self, wallet_name: str, ledger_id: str
    ) -> WalletManagerUsecase:
        wallet_config, err = self.config.block_rader.wallets.get_wallet(wallet_name)
        if err or not wallet_config:
            raise ValueError(f"WalletConfig not found for wallet_name {wallet_name}")

        # Find ledger_config from config
        ledger_config = next(
            (
                ledger_item
                for ledger_item in self.config.ledger.ledgers
                if ledger_item.ledger_id == ledger_id
            ),
            None,
        )
        if not ledger_config:
            raise ValueError(f"LedgerConfig not found for ledger_id {ledger_id}")

        manager = WalletManager(self.config.block_rader, wallet_config.wallet_id)

        return WalletManagerUsecase(
            service=self.wallet_service,
            manager=manager,
            wallet_config=wallet_config,
            ledger_config=ledger_config,
        )


# Helper function to be used by tasks
def get_task_wallet_manager_usecase(
    config: Config, wallet_name: str, ledger_id: str
) -> WalletManagerUsecase:
    session = get_session()
    factory = TaskDependenciesFactory(session, config)
    return factory.get_wallet_manager_usecase(wallet_name, ledger_id)
