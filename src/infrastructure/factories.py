from src.infrastructure.config_settings import load_config
from src.infrastructure.repositories import (
    AssetRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.services import (
    LedgerService,
    PaycrestService,
    WalletManager,
)
from src.usecases import TransactionUsecase, WalletManagerUsecase, WalletService


def get_wallet_manager_usecase_for_task() -> WalletManagerUsecase:
    config = load_config()

    # Initialize Repositories
    user_repository = UserRepository()
    wallet_repository = WalletRepository()
    asset_repository = AssetRepository()

    # Initialize Services
    ledger_service = LedgerService(config.ledger_config)
    paycrest_service = PaycrestService(config.paycrest_config)

    # Initialize Usecases
    transaction_usecase = TransactionUsecase(
        user_repository=user_repository,
        wallet_repository=wallet_repository,
        asset_repository=asset_repository,
        ledger_service=ledger_service,
    )

    # Initialize WalletService
    wallet_service = WalletService(
        blockrader_config=config.blockrader_config,
        ledger_service=ledger_service,
        user_repository=user_repository,
        wallet_repository=wallet_repository,
        asset_repository=asset_repository,
        paycrest_service=paycrest_service,
        transaction_usecase=transaction_usecase,
    )

    # Hardcode wallet_id and ledger_config for now, this needs to be passed dynamically or configured
    # For now, let's assume a default wallet and ledger are used for background tasks
    # In a real scenario, this would likely be part of the task arguments or a more sophisticated lookup
    default_wallet_id = config.blockrader_config.wallets.wallets[0].wallet_id if config.blockrader_config.wallets and config.blockrader_config.wallets.wallets else "default_wallet_id"
    default_ledger = config.ledger_config.ledgers[0] if config.ledger_config.ledgers else None


    if not default_ledger:
        raise ValueError("No default ledger configured for background tasks")

    # Instantiate WalletManager for WalletManagerUsecase
    wallet_config = next(
        (
            w
            for w in config.blockrader_config.wallets.wallets
            if w.wallet_id == default_wallet_id
        ),
        None,
    )
    if not wallet_config:
        raise ValueError(f"WalletConfig not found for wallet_id {default_wallet_id}")

    manager = WalletManager(config.blockrader_config, default_wallet_id)

    wallet_manager_usecase = WalletManagerUsecase(
        service=wallet_service,
        manager=manager,
        wallet_config=wallet_config,
        ledger_config=default_ledger,
    )
    return wallet_manager_usecase
