from fastapi import APIRouter

from src.api.versions.v1.handlers import (
    accounts_router,
    auth_router,
    misc_router,
    transactions_router,
    verify_router,
    wallet_router,
    webhook_router,
)
from src.infrastructure.logger import get_logger

logger = get_logger(__name__)

v1_router = APIRouter(prefix="/v1")


v1_router.include_router(auth_router.router)
v1_router.include_router(accounts_router.router)
v1_router.include_router(transactions_router.router)
v1_router.include_router(wallet_router.router)
v1_router.include_router(verify_router.router)
v1_router.include_router(webhook_router.router)
v1_router.include_router(misc_router.router)
