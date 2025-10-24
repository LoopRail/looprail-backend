from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.db import get_session
from src.infrastructure.repositories import (SQLUserRepository,
                                             SQLWalletRepository)
from src.infrastructure.services.paycrest.paycrest_service import \
    PaycrestService
from src.infrastructure.services.paystack_client import PaystackService
from src.infrastructure.settings import (BlockRaderConfig, block_rader_config,
                                         paycrest_config, paystack_config)
from src.models.user_model import UserRepository
from src.models.wallet_model import WalletRepository
from src.usecases.user_usecases import UserUseCase


async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    yield SQLUserRepository(session)


async def get_wallet_repository(
    session: AsyncSession = Depends(get_session),
) -> WalletRepository:
    yield SQLWalletRepository(session)


def get_blockrader_config() -> BlockRaderConfig:
    return block_rader_config


async def get_paycrest_service() -> PaycrestService:
    yield PaycrestService(paycrest_config)


async def get_paystack_service() -> PaystackService:
    yield PaystackService(paystack_config)


async def get_user_usecases(
    user_repository: UserRepository = Depends(get_user_repository),
    wallet_repository: WalletRepository = Depends(get_wallet_repository),
    blockrader_config: BlockRaderConfig = Depends(get_blockrader_config),
) -> UserUseCase:
    yield UserUseCase(user_repository, wallet_repository, blockrader_config)
