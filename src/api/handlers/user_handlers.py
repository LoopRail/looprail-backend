# src/looprail_backend/handlers/user_handlers.py
from uuid import UUID
from fastapi import Depends, HTTPException

from ...usecases.user_usecases import UserUseCases
from ..dependencies import get_user_usecases
from ...dtos.user_dtos import UserCreate, UserPublic


def create_user(
    user_data: UserCreate, user_usecases: UserUseCases = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to create a new user."""
    try:
        created_user = user_usecases.create_user(
            username=user_data.username, email=user_data.email
        )
        return created_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def get_user(user_id: UUID, user_usecases: UserUseCases = Depends(get_user_usecases)) -> UserPublic:
    """API endpoint to retrieve a user by their ID."""
    user = user_usecases.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=44, detail="User not found")
    return user
