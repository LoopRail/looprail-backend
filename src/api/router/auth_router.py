from fastapi import APIRouter

from src.api.router.user_router import create_user
from src.dtos import user_dtos

router = APIRouter(prefix="/auth", tags=["Auth"])

router.post("/register", response_model=user_dtos.UserPublic, status_code=201)(create_user)
