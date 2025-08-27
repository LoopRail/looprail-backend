# src/looprail_backend/core/domain/repositories.py
# This file defines the interfaces for the data access layer. These are abstract contracts
# that the application layer will use to interact with data, without knowing the details of
# the underlying data source (e.g., SQL database, NoSQL database, in-memory store).

# The actual implementations of these interfaces are located in the infrastructure layer.
# This separation is a key principle of Clean Architecture, promoting loose coupling and testability.

# --- Example ---
# The following is an example of a repository interface for the User entity.
# It defines the methods that any user repository implementation must provide.

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from .models import User

class AbstractUserRepository(ABC):
    """Abstract interface for a user repository."""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Retrieves a user by their unique ID."""
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        raise NotImplementedError

    @abstractmethod
    def add(self, user: User) -> None:
        """Adds a new user to the repository."""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[User]:
        """Lists all users."""
        raise NotImplementedError
