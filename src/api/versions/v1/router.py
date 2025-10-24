from fastapi import APIRouter

from src.api.versions.v1.handlers import accounts_router, auth_router, offramp_router

v1_router = APIRouter(prefix="/v1")


v1_router.include_router(auth_router.router)
v1_router.include_router(accounts_router.router)
v1_router.include_router(offramp_router.router)
