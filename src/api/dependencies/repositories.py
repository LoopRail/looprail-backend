from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.repositories import (
    AssetRepository,
    RefreshTokenRepository,
    SessionRepository,
    TransactionRepository,
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


async def get_transaction_repository(
    session: AsyncSession = Depends(get_session),
) -> TransactionRepository:
    yield TransactionRepository(session)


async def get_asset_repository(
    session: AsyncSession = Depends(get_session),
) -> AssetRepository:
    yield AssetRepository(session)


async def get_session_repository(
    session: AsyncSession = Depends(get_session),
) -> SessionRepository:
    yield SessionRepository(session)


async def get_refresh_token_repository(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepository:
    yield RefreshTokenRepository(session)
