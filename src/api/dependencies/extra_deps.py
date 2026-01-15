from fastapi import Request

from src.infrastructure.config_settings import Config, load_config
from src.infrastructure.redis import RQManager
from src.infrastructure.settings import ENVIRONMENT


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_app_environment(request: Request) -> ENVIRONMENT:
    return request.app.state.environment


def get_rq_manager() -> RQManager:
    config = load_config()
    return RQManager(config.redis)
