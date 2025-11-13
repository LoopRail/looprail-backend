from typing import Optional, Tuple, TypeVar

from src.infrastructure.db.unit_of_work import UnitOfWork
from src.types.error import Error, error

T = TypeVar("T")


class BaseRepository:
    """
    Base class for repositories to provide common functionality like session management.
    Transaction handling will be managed externally via UnitOfWork.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    @property
    def session(self):
        return self.uow.session
