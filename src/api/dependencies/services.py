from fastapi import Depends, Request

from src.infrastructure.redis import RedisClient, RQManager
from src.infrastructure.services import (
    AuthLockService,
    CacheService,
    GeolocationService,
    LedgerService,
    LockService,
    PaycrestService,
    PaystackService,
    ResendService,
)
from src.infrastructure.settings import BlockRaderConfig, PayCrestConfig


def get_blockrader_config(request: Request) -> BlockRaderConfig:
    return request.app.state.blockrader_config


def get_ledger_config(request: Request) -> BlockRaderConfig:
    return request.app.state.ledger_config


def get_paycrest_config(request: Request) -> PayCrestConfig:
    return request.app.state.paycrest_config


def get_ledger_service(request: Request) -> LedgerService:
    return request.app.state.ledger_service


def get_paycrest_service(request: Request) -> PaycrestService:
    return request.app.state.paycrest


def get_paystack_service(request: Request) -> PaystackService:
    return request.app.state.paystack


def get_resend_service(request: Request) -> ResendService:
    return request.app.state.resend


def get_geolocation_service(request: Request) -> GeolocationService:
    return request.app.state.geolocation


def get_redis_service(request: Request) -> RedisClient:
    return request.app.state.redis


def get_rq_manager(request: Request) -> RQManager:
    return request.app.state.rq_manager


def get_cache_service(
    redis_client: RedisClient = Depends(get_redis_service),
) -> CacheService:
    return CacheService(redis_client)


def get_auth_lock_service(subject) -> AuthLockService:
    def func(request: Request):
        return request.app.state.auth_lock.set_subject(subject)

    return func


def get_lock_service(
    redis_client: RedisClient = Depends(get_redis_service),
) -> LockService:
    return LockService(redis_client)


def get_custom_rate_limiter(
    redis_client: RedisClient = Depends(get_redis_service),
) -> "CustomRateLimiter":
    from src.api.rate_limiters.limiters import CustomRateLimiter

    return CustomRateLimiter(redis_client)
