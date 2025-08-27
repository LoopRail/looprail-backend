# src/looprail_backend/core/domain/models.py
# This file defines the core business objects of the application, known as Entities or Domain Models.
# These are plain Python objects that encapsulate the data and behavior of the business domain.
# They should not have any dependencies on external frameworks or libraries (like databases or web frameworks).

# --- Example ---
# The following is a simple example of a User entity.
# It uses Python's dataclasses for simplicity, but any plain Python class will do.

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class User:
    """Represents a user in the system."""

    id: UUID
    username: str
    email: str

    @staticmethod
    def create(username: str, email: str) -> "User":
        """Factory method to create a new User with a generated ID."""
        return User(id=uuid4(), username=username, email=email)
