from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from src.api.dependencies.repositories import (
    get_refresh_token_repository,
    get_session_repository,
    get_transaction_repository,
    get_user_repository,
    get_wallet_repository,
)
from src.api.dependencies.services import get_blockrader_config, get_redis_service
from src.infrastructure import config
from src.infrastructure.redis import RedisClient
from src.infrastructure.repositories import (
    RefreshTokenRepository,
    SessionRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.settings import BlockRaderConfig
from src.usecases import (
    JWTUsecase,
    OtpUseCase,
    SecretsUsecase,
    SessionUseCase,
    UserUseCase,
    WalletManagerUsecase,
    WalletService,
)
from src.usecases.transaction_usecases import TransactionUsecase
from src.types import Chain


async def get_session_usecase(
    session_repository: SessionRepository = Depends(get_session_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
) -> SessionUseCase:
    yield SessionUseCase(session_repository, refresh_token_repository)


async def get_user_usecases(
    request: Request,
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
) -> UserUseCase:
    argon2_config = request.app.state.argon2_config
    yield UserUseCase(
        user_repository, wallet_repository, blockrader_config, argon2_config
    )


async def get_otp_usecase(
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


async def get_jwt_usecase():
    yield JWTUsecase(config.jwt)


async def get_blockrader_wallet_service(
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
):
    # NOTE: This dependency seems to be missing `ledger_service_config` for WalletService
    return WalletService(
        blockrader_config,
        user_repository,
        wallet_repository,
    )


async def get_wallet_manager_factory(
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
) -> Callable[[Chain], "WalletManagerUsecase"]:
    def factory(wallet_id: str):
        wallet_config = next(
            (
                w
                for w in config.block_rader.wallets
                if w.wallet_id == wallet_id and w.active
            ),
            None,
        )
        if not wallet_config:
            return None

        return wallet_service.new_wallet_manager(
            wallet_config.wallet_id, wallet_config.chain
        )

    return factory


def get_transaction_usecase(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
) -> TransactionUsecase:
    return TransactionUsecase(transaction_repo)
