import os

from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.infrastructure import get_logger
from src.infrastructure.settings import ENVIRONMENT

logger = get_logger(__name__)

logger.debug("ENVIRONMENT is %s", os.getenv("ENVIRONMENT"))
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") != ENVIRONMENT.TEST.value,
)
logger.debug("Limiter enabled status: %s", limiter.enabled)


def add_rate_limiter(app: FastAPI):
    if os.getenv("ENVIRONMENT") == ENVIRONMENT.TEST.value:
        return
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
