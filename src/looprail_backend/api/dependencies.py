# src/looprail_backend/api/dependencies.py
# This file is responsible for creating and providing dependencies to the API layer.
# In this case, it sets up and provides the `UserService`.

# This is a form of dependency injection. It allows the API routes to simply "ask for"
# a service without needing to know how it's created or what its own dependencies are.

# --- Example ---
# The following function creates a `UserService` instance using the `InMemoryUserRepository`.
# In a real application, you could have logic here to decide which repository to use
# based on an environment variable (e.g., use a real database in production).

from ..core.application.services import UserService
from ..infrastructure.persistence.repositories import InMemoryUserRepository

# Create a single, shared instance of the repository.
# In a real app, you might manage this lifecycle differently (e.g., per-request).
user_repository = InMemoryUserRepository()

def get_user_service() -> UserService:
    """Dependency provider for the UserService."""
    return UserService(user_repository)
