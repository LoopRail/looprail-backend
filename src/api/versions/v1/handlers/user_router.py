from fastapi import APIRouter, Depends, HTTPException
from src.infrastructure.logger import get_logger

from src.api.dependencies import get_user_usecases
from src.dtos.user_dtos import UserPublic
from src.usecases import UserUseCase
from src.types.common_types import UserId

logger = get_logger(__name__)

# Create a new router for user-related endpoints
router = APIRouter(prefix="/users", tags=["Users"])

# --- API Endpoints ---


async def get_user(
    user_id: UserId, user_usecases: UserUseCase = Depends(get_user_usecases)
) -> UserPublic:
    """API endpoint to retrieve a user by their ID."""
    logger.info("Fetching user with ID: %s", user_id)
    user, err = await user_usecases.get_user_by_id(user_id)
    if err:
        logger.error("Error fetching user %s: %s", user_id, err.message)
        raise HTTPException(status_code=404, detail=err.message)
    return user


# router.get("/{user_id}", response_model=UserPublic, response_model_exclude_none=True)(get_user)
