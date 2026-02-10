import os
from functools import wraps
from typing import Any, Callable, Coroutine

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.dependencies.services import get_redis_service
from src.api.rate_limiters.limiters import CustomRateLimiter, limiter
from src.infrastructure import get_logger
from src.infrastructure.services import RedisClient
from src.infrastructure.settings import ENVIRONMENT

logger = get_logger(__name__)


def get_custom_rate_limiter(
    redis_client: RedisClient = Depends(get_redis_service),
) -> CustomRateLimiter:
    return CustomRateLimiter(redis_client)


def custom_rate_limiter(
    limit_type: str,
    identifier_arg: str,
    identifier_field: str,
):
    """
    A decorator to apply custom rate limiting to FastAPI endpoints.
    """

    def wrapper_decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper_function(
            request: Request,
            *args,
            custom_limiter: CustomRateLimiter = Depends(get_custom_rate_limiter),
            **kwargs,
        ):
            if os.getenv("ENVIRONMENT") == ENVIRONMENT.TEST.value:
                return await func(request, *args, **kwargs)

            identifier_object = kwargs.get(identifier_arg)
            if not identifier_object:
                logger.error(
                    "Rate limiter: Identifier argument '%s' not found in endpoint kwargs.",
                    identifier_arg,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Rate limiter configuration error: Missing identifier argument.",
                )

            identifier_value = getattr(identifier_object, identifier_field, None)
            if not identifier_value:
                logger.error(
                    "Rate limiter: Identifier field '%s' not found in '%s' object.",
                    identifier_field,
                    identifier_arg,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Rate limiter configuration error: Missing identifier field.",
                )

            (
                allowed,
                error_msg,
                attempts,
                retry_after_value,
            ) = await custom_limiter.check_limit(
                limit_type,
                request,
                identifier_value=identifier_value,
            )

            if not allowed:
                detail = {"message": error_msg}
                if attempts is not None:
                    detail["attempt"] = attempts

                headers = {}
                if retry_after_value is not None:
                    headers["Retry-After"] = str(retry_after_value)

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=detail,
                    headers=headers,
                )

            return await func(request, custom_limiter, *args, **kwargs)

        return wrapper_function

    return wrapper_decorator


def add_rate_limiter(app: FastAPI):
    if os.getenv("ENVIRONMENT") == ENVIRONMENT.TEST.value:
        return
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

