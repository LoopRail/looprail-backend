from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.db import get_session
from src.infrastructure.repositories import (UserRepository,
                                             WalletRepository)


async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    yield UserRepository(session)


async def get_wallet_repository(
    session: AsyncSession = Depends(get_session),
) -> WalletRepository:
    yield WalletRepository(session)


