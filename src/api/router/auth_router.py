from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_user_usecases
from src.dtos.user_dtos import UserCreate, UserPublic
from src.infrastructure.logger import get_logger
from src.usecases.user_usecases import UserUseCase

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


async def create_user(
    user_data: UserCreate, user_usecases: UserUseCase = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to create a new user."""
    created_user, err = await user_usecases.create_user(user_create=user_data)
    if err:
        logger.error(f"Failed to create user: {err.message}")
        raise HTTPException(status_code=400, detail=err.message)
    logger.info(f"User {created_user.username} registered successfully.")
    return created_user


router.post("/register", response_model=UserPublic, status_code=201)(create_user)
