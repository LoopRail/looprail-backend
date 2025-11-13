from typing import Optional, Tuple, TypeVar

from sqlmodel.ext.asyncio.session import AsyncSession

from src.types.error import Error, error

T = TypeVar("T")


class BaseRepository:
    """
    Base class for repositories to provide common functionality like session management.
    Transaction handling will be managed externally.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
