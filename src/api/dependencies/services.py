from fastapi import Depends

from src.infrastructure import RedisClient, redis_config
from src.infrastructure.services import (AuthLockService, PaycrestService,
                                         PaystackService, ResendService)
from src.infrastructure.settings import (BlockRaderConfig, block_rader_config,
                                         paycrest_config, paystack_config,
                                         resend_config)


def get_blockrader_config() -> BlockRaderConfig:
    return block_rader_config


async def get_paycrest_service() -> PaycrestService:
    yield PaycrestService(paycrest_config)


async def get_paystack_service() -> PaystackService:
    yield PaystackService(paystack_config)


async def get_resend_service() -> ResendService:
    yield ResendService(resend_config)


async def get_redis_service() -> RedisClient:
    yield RedisClient(redis_config)


async def get_auth_lock_service(
    redis_client: RedisClient = Depends(get_redis_service),
) -> AuthLockService:
    yield AuthLockService(redis_client=redis_client.redis)
