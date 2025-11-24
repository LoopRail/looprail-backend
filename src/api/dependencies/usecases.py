from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from src.api.dependencies.repositories import (get_user_repository,
                                               get_wallet_provider_repository,
                                               get_wallet_repository)
from src.api.dependencies.services import (get_blockrader_config,
                                           get_redis_service)
from src.infrastructure import RedisClient, jwt_config, otp_config
from src.infrastructure.repositories import (UserRepository,
                                             WalletProviderRepository,
                                             WalletRepository)
from src.infrastructure.settings import BlockRaderConfig
from src.usecases import JWTUsecase, OtpUseCase, UserUseCase, WalletService


async def get_user_usecases(
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
) -> UserUseCase:
    yield UserUseCase(user_repository, wallet_repository, blockrader_config)


async def get_otp_usecase(
    redis_client: RedisClient = Depends(get_redis_service),
) -> OtpUseCase:
    yield OtpUseCase(redis_client, otp_config)


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
    yield JWTUsecase(jwt_config)


async def get_blockrader_wallet_service(
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
    wallet_provider_repository: WalletProviderRepository = Depends(
        get_wallet_provider_repository
    ),
):
    return WalletService(
        blockrader_config,
        user_repository,
        wallet_repository,
        wallet_provider_repository,
    )


async def get_blockrader_base_wallet_wallet_manager(
    wallet_serivce: WalletService = Depends(get_blockrader_wallet_service),
    blokrader_config: BlockRaderConfig = Depends(get_blockrader_config),
):
    return wallet_serivce.new_wallet_manager(blokrader_config.base_master_wallet_id)
