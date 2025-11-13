from typing import AsyncIterator

from sqlmodel.ext.asyncio.session import AsyncSession

from src.infrastructure.db import session_factory


class UnitOfWork:
    """
    Manages the lifecycle of an AsyncSession and provides explicit transaction control.
    """

    def __init__(self):
        self.session_factory = session_factory

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()

    async def commit(self):
        """Explicitly commits the current transaction."""
        await self.session.commit()

    async def rollback(self):
        """Explicitly rolls back the current transaction."""
        await self.session.rollback()

    @property
    def session(self) -> AsyncSession:
        """Provides access to the underlying AsyncSession."""
        return self._session

    @session.setter
    def session(self, value: AsyncSession):
        self._session = value
