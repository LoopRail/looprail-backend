from src.infrastructure import RedisClient, redis_config
from src.infrastructure.services import ResendService
from src.infrastructure.services.paycrest.paycrest_service import \
    PaycrestService
from src.infrastructure.services.paystack_client import PaystackService
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
