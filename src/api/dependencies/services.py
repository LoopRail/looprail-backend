from fastapi import Depends

from src.infrastructure import RedisClient, config
from src.infrastructure.services import (AuthLockService, PaycrestService,
                                         PaystackService, ResendService)
from src.infrastructure.settings import BlockRaderConfig


def get_blockrader_config() -> BlockRaderConfig:
    return config.block_rader


async def get_paycrest_service() -> PaycrestService:
    yield PaycrestService(config.paycrest)


async def get_paystack_service() -> PaystackService:
    yield PaystackService(config.paystack)


async def get_resend_service() -> ResendService:
    yield ResendService(config.resend)


async def get_redis_service() -> RedisClient:
    yield RedisClient(config.redis)


async def get_auth_lock_service(
    redis_client: RedisClient = Depends(get_redis_service),
) -> AuthLockService:
    yield AuthLockService(redis_client=redis_client.redis)
