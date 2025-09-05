from fastapi import APIRouter
from src.api.handlers import user_handlers
from src.dtos import user_dtos

router = APIRouter(prefix="/auth", tags=["Auth"])

router.post("/register", response_model=user_dtos.UserPublic, status_code=201)(user_handlers.create_user)