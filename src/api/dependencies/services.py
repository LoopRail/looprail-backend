from fastapi import Request

from src.infrastructure import RedisClient
from src.infrastructure.services import (
    AuthLockService,
    PaycrestService,
    PaystackService,
    ResendService,
)
from src.infrastructure.settings import BlockRaderConfig


def get_blockrader_config(request: Request) -> BlockRaderConfig:
    return request.app.state.blockrader_config


def get_paycrest_service(request: Request) -> PaycrestService:
    return request.app.state.paycrest


def get_paystack_service(request: Request) -> PaystackService:
    return request.app.state.paystack


def get_resend_service(request: Request) -> ResendService:
    return request.app.state.resend


def get_redis_service(request: Request) -> RedisClient:
    return request.app.state.redis


def get_auth_lock_service(request: Request) -> AuthLockService:
    return request.app.state.auth_lock
