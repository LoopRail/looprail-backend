from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from src.api.dependencies.extra_deps import get_config
from src.api.dependencies.repositories import (get_asset_repository,
                                               get_refresh_token_repository,
                                               get_session_repository,
                                               get_transaction_repository,
                                               get_user_repository,
                                               get_wallet_repository)
from src.api.dependencies.services import (get_blockrader_config,
                                           get_ledger_config,
                                           get_ledger_service,
                                           get_paycrest_service,
                                           get_redis_service)
from src.infrastructure import CUSTOMER_WALLET_LEDGER, MASTER_BASE_WALLET
from src.infrastructure.config_settings import Config
from src.infrastructure.redis import RedisClient
from src.infrastructure.repositories import (AssetRepository,
                                             RefreshTokenRepository,
                                             SessionRepository,
                                             TransactionRepository,
                                             UserRepository, WalletRepository)
from src.infrastructure.services import LedgerService, PaycrestService
from src.infrastructure.settings import BlockRaderConfig
from src.types import LedgerConfig
from src.usecases import (JWTUsecase, OtpUseCase, SecretsUsecase,
                          SessionUseCase, TransactionUsecase, UserUseCase,
                          WalletManagerUsecase, WalletService)


async def get_session_usecase(
    session_repository: SessionRepository = Depends(get_session_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
) -> SessionUseCase:
    yield SessionUseCase(session_repository, refresh_token_repository)


async def get_otp_usecase(
    config: Config = Depends(get_config),
    redis_client: RedisClient = Depends(get_redis_service),
) -> OtpUseCase:
    yield OtpUseCase(redis_client, config.otp)


async def get_secrets_usecase(
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
) -> SecretsUsecase:
    yield SecretsUsecase(blockrader_config)


async def get_otp_token(
    x_otp_token: Optional[str] = Header(default=None, description="OTP token"),
):
    if x_otp_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X_OTP_TOKEN header not provided",
        )
    return x_otp_token


async def get_jwt_usecase(config: Config = Depends(get_config)):
    yield JWTUsecase(config.jwt)


def get_transaction_usecase(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
) -> TransactionUsecase:
    return TransactionUsecase(transaction_repo)


async def get_blockrader_wallet_service(
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
    asset_repository: AssetRepository = Depends(get_asset_repository),
    ledger_service: LedgerService = Depends(get_ledger_service),
    paycrest_service: PaycrestService = Depends(get_paycrest_service),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
):
    return WalletService(
        blockrader_config=blockrader_config,
        user_repository=user_repository,
        wallet_repository=wallet_repository,
        asset_repository=asset_repository,
        ledger_service=ledger_service,
        paycrest_service=paycrest_service,
        transaction_usecase=transaction_usecase,
    )


async def get_wallet_manager_usecase(
    ledger_config: LedgerConfig = Depends(get_ledger_config),
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
) -> WalletManagerUsecase:
    ledger, err = ledger_config.ledgers.get_ledger(CUSTOMER_WALLET_LEDGER)
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to get legder with name {CUSTOMER_WALLET_LEDGER}"},
        )
    base_master_wallet, err = wallet_service.blockrader_config.wallets.get_wallet(
        MASTER_BASE_WALLET
    )
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to get blockrader wallet {MASTER_BASE_WALLET}"},
        )
    wallet_manager, err = wallet_service.new_manager(
        base_master_wallet.wallet_id, ledger
    )
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to create wallet manager: {err.message}"},
        )
    return wallet_manager


async def get_user_usecases(
    request: Request,
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
    wallet_manager_usecase: WalletManagerUsecase = Depends(get_wallet_manager_usecase),
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
) -> UserUseCase:
    argon2_config = request.app.state.argon2_config
    yield UserUseCase(
        user_repository,
        wallet_repository,
        blockrader_config,
        argon2_config,
        wallet_manager_usecase,
        wallet_service,  # Added this line
    )
