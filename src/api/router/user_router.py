from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_user_usecases
from src.dtos.user_dtos import UserPublic
from src.usecases.user_usecases import UserUseCases

# Create a new router for user-related endpoints
router = APIRouter(prefix="/users", tags=["Users"])

# --- API Endpoints ---


async def get_user(
    user_id: UUID, user_usecases: UserUseCases = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to retrieve a user by their ID."""
    user, err = await user_usecases.get_user_by_id(user_id)
    if err:
        raise HTTPException(status_code=404, detail=err.message)
    return user


router.get("/{user_id}", response_model=UserPublic)(get_user)
