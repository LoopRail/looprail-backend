from fastapi import Depends, Request

from src.infrastructure.config_settings import Config, load_config
from src.infrastructure.redis import RQManager
from src.infrastructure.services import RedisClient
from src.infrastructure.settings import ENVIRONMENT
from src.api.rate_limiter import CustomRateLimiter
from src.api.dependencies.services import get_redis_service


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_app_environment(request: Request) -> ENVIRONMENT:
    return request.app.state.environment


def get_rq_manager() -> RQManager:
    config = load_config()
    return RQManager(config.redis)


def get_custom_rate_limiter(
    redis_client: RedisClient = Depends(get_redis_service),
) -> CustomRateLimiter:
    return CustomRateLimiter(redis_client)
