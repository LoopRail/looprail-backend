from typing import Optional, Protocol
from uuid import UUID

from .models import User


class UserRepository(Protocol):
    """
    Protocol for a user repository.
    Defines the interface for interacting with user data.
    """

    def add(self, user: User) -> None:
        ...

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        ...

    def get_by_username(self, username: str) -> Optional[User]:
        ...

    def list_all(self) -> list[User]:
        ...
