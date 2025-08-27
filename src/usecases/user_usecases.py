# src/looprail_backend/usecases/user_usecases.py
# This file contains the application services or use cases. It orchestrates the flow of data
# and calls the domain objects to perform business operations.

# The services in this layer are responsible for handling application-specific logic.
# They depend on the domain layer's abstract repositories, not on concrete implementations.
# This keeps the application logic separate from the infrastructure details.

# --- Example ---
# The following is an example of a user service that handles user creation and retrieval.
# It depends on the UserRepository defined in the domain layer.

from typing import Optional
from uuid import UUID

from ..domain.models import User
from ..domain.repositories import UserRepository


class UserUseCases:
    """Provides application services related to users."""

    def __init__(self, user_repository: UserRepository):
        """Initializes the service with a user repository."""
        self._repository = user_repository

    def create_user(self, username: str, email: str) -> User:
        """
        Creates a new user.

        This is a simple use case. In a real application, it might involve more steps,
        like checking for duplicate usernames, validating input, or sending a welcome email.
        """
        print(f"Service: Creating user '{username}' with email '{email}'")
        new_user = User.create(username=username, email=email)
        self._repository.add(new_user)
        return new_user

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Retrieves a user by their ID."""
        print(f"Service: Getting user with ID '{user_id}'")
        return self._repository.get_by_id(user_id)
