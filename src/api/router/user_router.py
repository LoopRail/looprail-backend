from fastapi import APIRouter

from src.api.handlers import user_handlers
from src.dtos import user_dtos

# Create a new router for user-related endpoints
router = APIRouter(prefix="/users", tags=["Users"])

# --- API Endpoints ---

router.post("/", response_model=user_dtos.UserPublic, status_code=201)(user_handlers.create_user)
router.get("/{user_id}", response_model=user_dtos.UserPublic)(user_handlers.get_user)