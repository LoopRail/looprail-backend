# src/looprail_backend/infrastructure/persistence/repositories.py
# This file provides the concrete implementations of the repository interfaces defined in the domain layer.
# This is where the application interacts with the actual database, ORM, or other data sources.

# By swapping out the implementation used, you can change the database technology without
# affecting the application or domain layers. For example, you could have an InMemoryUserRepository
# for testing and a PostgresUserRepository for production.

# --- Example ---
# The following is a simple in-memory implementation of the user repository.
# It uses a dictionary to store users, which is useful for development and testing.

from typing import Optional
from uuid import UUID

from ...core.domain.models import User


class InMemoryUserRepository:
    """In-memory implementation of the user repository."""

    def __init__(self):
        self._users: dict[UUID, User] = {}

    def add(self, user: User) -> None:
        print(f"Repository: Adding user {user.username} to in-memory store.")
        self._users[user.id] = user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        print(f"Repository: Getting user with ID {user_id} from in-memory store.")
        return self._users.get(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        print(
            f"Repository: Getting user with username {username} from in-memory store."
        )
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def list_all(self) -> list[User]:
        print("Repository: Listing all users from in-memory store.")
        return list(self._users.values())
