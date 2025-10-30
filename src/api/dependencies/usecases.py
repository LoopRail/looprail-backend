from fastapi import Depends

from src.api.dependencies.repositories import get_user_repository, get_wallet_repository
from src.api.dependencies.services import get_blockrader_config, get_redis_service
from src.infrastructure import RedisClient, otp_config
from src.infrastructure.settings import BlockRaderConfig
from src.models.user_model import UserRepository
from src.models.wallet_model import WalletRepository
from src.usecases import OtpUseCase, UserUseCase


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
