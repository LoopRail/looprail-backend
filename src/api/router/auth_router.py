from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.usecases.user_usecases import UserUseCases
from src.api.dependencies import get_user_usecases
from src.dtos.user_dtos import UserCreate, UserPublic

router = APIRouter(prefix="/auth", tags=["Auth"])

async def create_user(
    user_data: UserCreate, user_usecases: UserUseCases = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to create a new user."""
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if err:
        raise HTTPException(status_code=400, detail=err.message)
    return created_user

router.post("/register", response_model=user_dtos.UserPublic, status_code=201)(create_user)