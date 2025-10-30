from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.db import get_session
from src.infrastructure.repositories import SQLUserRepository, SQLWalletRepository
from src.models.user_model import UserRepository
from src.models.wallet_model import WalletRepository


async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    yield SQLUserRepository(session)


async def get_wallet_repository(
    session: AsyncSession = Depends(get_session),
) -> WalletRepository:
    yield SQLWalletRepository(session)
