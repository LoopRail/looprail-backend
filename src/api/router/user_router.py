# src/looprail_backend/router/user_router.py
from fastapi import APIRouter

from ..handlers import user_handlers
from ...dtos import user_dtos

# Create a new router for user-related endpoints
router = APIRouter()

# --- API Endpoints ---

router.post("/users/", response_model=user_dtos.UserPublic, status_code=201)(user_handlers.create_user)
router.get("/users/{user_id}", response_model=user_dtos.UserPublic)(user_handlers.get_user)
