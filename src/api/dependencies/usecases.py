from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from src.api.dependencies.extra_deps import get_current_user
from src.api.dependencies.repositories import (
    get_asset_repository,
    get_refresh_token_repository,
    get_session_repository,
    get_transaction_repository,
    get_user_repository,
    get_wallet_repository,
)
from src.api.dependencies.services import (get_blockrader_config,
                                           get_ledger_service,
                                           get_paystack_service,
                                           get_redis_service)
from src.infrastructure import config
from src.infrastructure.redis import RedisClient
from src.infrastructure.repositories import (
    AssetRepository,
    RefreshTokenRepository,
    SessionRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.services import LedgerService, PaystackService
from src.infrastructure.settings import BlockRaderConfig, LedgderServiceConfig
from src.models import User, Wallet
from src.types import Chain
from src.types.error import error
from src.usecases import (
    JWTUsecase,
    OtpUseCase,
    SecretsUsecase,
    SessionUseCase,
    UserUseCase,
    WalletManagerUsecase,
    WalletService,
)
from src.usecases.transaction_usecases import TransactionUsecase, get_transaction_usecase


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
    asset_repository: AssetRepository = Depends(get_asset_repository),
    ledger_service_config: LedgderServiceConfig = config.ledger_service,
    ledger_service: LedgerService = Depends(get_ledger_service),
    paystack_service: PaystackService = Depends(get_paystack_service),
    transaction_usecase: TransactionUsecase = Depends(get_transaction_usecase),
):
    return WalletService(
        blockrader_config=blockrader_config,
        user_repository=user_repository,
        wallet_repository=wallet_repository,
        asset_repository=asset_repository,
        ledger_service_config=ledger_service_config,
        ledger_service=ledger_service,
        paystack_service=paystack_service,
        transaction_usecase=transaction_usecase,
    )


async def get_wallet_manager_usecase(
    user: User = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_blockrader_wallet_service),
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
) -> WalletManagerUsecase:
    # Get user's active wallet
    wallets, err = await wallet_repository.get_wallets_by_user_id(user_id=user.id)
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to retrieve user wallets: {err.message}"},
        )
    if not wallets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No active wallet found for the user."},
        )
    
    # Assuming the first active wallet is the one to use
    user_wallet = next((w for w in wallets if w.is_active), None)
    if not user_wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No active wallet found for the user."},
        )

    # Get ledger config
    ledger_config = next(
        (
            ledger_entry
            for ledger_entry in config.ledger_service.ledgers.ledgers
            if ledger_entry.id == user_wallet.chain.value
        ),
        None,
    )

    if not ledger_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Ledger configuration not found for wallet chain."},
        )

    wallet_manager, err = wallet_service.new_manager(user_wallet.id, ledger_config)
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Failed to create wallet manager: {err.message}"},
        )
    return wallet_manager


def get_transaction_usecase(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
) -> TransactionUsecase:
    return TransactionUsecase(transaction_repo)
