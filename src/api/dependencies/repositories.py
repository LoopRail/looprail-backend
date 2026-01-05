from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.repositories import (
    RefreshTokenRepository,
    SessionRepository,
    UserRepository,
    WalletRepository,
)
from src.infrastructure.db import get_session

async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    yield UserRepository(session)


async def get_wallet_repository(
    session: AsyncSession = Depends(get_session),
) -> WalletRepository:
    yield WalletRepository(session)


async def get_session_repository(
    session: AsyncSession = Depends(get_session),
) -> SessionRepository:
    yield SessionRepository(session)


async def get_refresh_token_repository(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepository:
    yield RefreshTokenRepository(session)
