from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.usecases.user_usecases import UserUseCases
from src.api.dependencies import get_user_usecases
from src.dtos.user_dtos import UserCreate, UserPublic

# Create a new router for user-related endpoints
router = APIRouter(prefix="/users", tags=["Users"])

# --- API Endpoints ---

async def create_user(
    user_data: UserCreate, user_usecases: UserUseCases = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to create a new user."""
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if err:
        raise HTTPException(status_code=400, detail=err.message)
    return created_user


async def get_user(
    user_id: UUID, user_usecases: UserUseCases = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to retrieve a user by their ID."""
    user, err = await user_usecases.get_user_by_id(user_id)
    if err:
        raise HTTPException(status_code=404, detail=err.message)
    return user

router.post("/", response_model=user_dtos.UserPublic, status_code=201)(create_user)
router.get("/{user_id}", response_model=user_dtos.UserPublic)(get_user)