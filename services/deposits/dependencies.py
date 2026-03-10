import functools
from contextlib import asynccontextmanager

from sqlmodel.ext.asyncio.session import AsyncSession
from rq import Queue

from src.infrastructure.config_settings import Config, load_config
from src.infrastructure.db import get_session
from src.infrastructure.redis import RedisClient, RQManager
from src.infrastructure.repositories import (
    AssetRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
    SessionRepository,
)
from src.infrastructure.services import (
    LedgerService,
    PaycrestService,
    WalletManager,
    LockService,
    GeolocationService,
)
from src.infrastructure.services.resend_service import ResendService
from src.usecases import TransactionUsecase, WalletManagerUsecase, WalletService
from src.usecases.notification_usecases import NotificationUseCase
from src.infrastructure.settings import RedisConfig, ResendConfig


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
    def transaction_repository(self) -> TransactionRepository:
        return TransactionRepository(self.session)

    @functools.cached_property
    def session_repository(self) -> SessionRepository:
        return SessionRepository(self.session)

    @functools.cached_property
    def ledger_service(self) -> LedgerService:
        return LedgerService(self.config.ledger)

    @functools.cached_property
    def paycrest_service(self) -> PaycrestService:
        return PaycrestService(self.config.paycrest)

    @functools.cached_property
    def transaction_usecase(self) -> TransactionUsecase:
        return TransactionUsecase(
            transaction_repo=self.transaction_repository,
        )

    @functools.cached_property
    def geolocation_service(self) -> GeolocationService:
        return GeolocationService()

    @functools.cached_property
    def wallet_service(self) -> WalletService:
        return WalletService(
            self.wallet_repository,
            config=self.config,
            blockrader_config=self.config.block_rader,
            ledger_service=self.ledger_service,
            user_repository=self.user_repository,
            asset_repository=self.asset_repository,
            paycrest_service=self.paycrest_service,
            transaction_usecase=self.transaction_usecase,
            geolocation_service=self.geolocation_service,
        )

    def get_wallet_manager_usecase(
        self, wallet_id: str, ledger_id: str
    ) -> WalletManagerUsecase:
        wallet_config, err = self.config.block_rader.wallets.get_wallet(
            wallet_id=wallet_id
        )
        if err or not wallet_config:
            raise ValueError(f"WalletConfig not found for wallet_name {wallet_id}")

        ledger_config, err = self.config.ledger.ledgers.get_ledger(ledger_id=ledger_id)
        if err:
            raise ValueError(f"LedgerConfig not found for ledger_id {ledger_id}")

        manager = WalletManager(self.config.block_rader, wallet_config.wallet_id)

        return WalletManagerUsecase(
            service=self.wallet_service,
            manager=manager,
            wallet_config=wallet_config,
            ledger_config=ledger_config,
        )

    @functools.cached_property
    def redis_client(self) -> RedisClient:
        return RedisClient(RedisConfig())

    @functools.cached_property
    def lock_service(self) -> LockService:
        return LockService(self.redis_client)

    @functools.cached_property
    def resend_service(self) -> ResendService:
        return ResendService(ResendConfig())

    @functools.cached_property
    def notification_usecase(self) -> NotificationUseCase:
        redis_config = RedisConfig()
        rq_manager = RQManager(redis_config)
        notif_queue = Queue("notifications", connection=rq_manager.get_connection())
        return NotificationUseCase(notif_queue)


@asynccontextmanager
async def get_task_dependencies_factory():
    config = load_config()
    async for session in get_session():
        yield TaskDependenciesFactory(session, config)


async def get_task_wallet_manager_usecase(
    wallet_id: str, ledger_id: str
) -> WalletManagerUsecase:
    async with get_task_dependencies_factory() as factory:
        return factory.get_wallet_manager_usecase(wallet_id, ledger_id)
