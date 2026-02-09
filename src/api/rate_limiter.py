import os
import random
import time
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Tuple

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.dependencies.extra_deps import get_custom_rate_limiter
from src.infrastructure import RedisClient, get_logger
from src.infrastructure.settings import ENVIRONMENT

# --- Rate Limiter Constants ---
# Redis Key Prefixes
RATE_LIMIT_BASE_PREFIX = "rate-limit:"

# Sub-keys for different rate limit components
SUB_KEY_EMAIL = "email"
SUB_KEY_IP = "ip"
SUB_KEY_ATTEMPTS = "attempts"
SUB_KEY_LAST = "last"
SUB_KEY_GLOBAL = "global"

# --- Rate Limit Configuration Registry ---
# Define configurations for different rate limit types
RATE_LIMIT_CONFIGS = {
    "otp": {
        # Email Limit (Sliding Window)
        "email_limit_count": 5,
        "email_limit_window_seconds": 3600,  # 1 hour
        "email_redis_expiry_seconds": 7200,  # 2 hours
        # IP Limit (Token Bucket)
        "ip_capacity": 20,
        "ip_refill_rate_per_hour": 10,
        "ip_refill_rate_per_second": 10 / 3600,
        "ip_redis_expiry_seconds": 7200,  # 2 hours
        # Progressive Delay
        "progressive_delays": {1: 0, 2: 0, 3: 30, 4: 120, 5: 900},
        "attempts_redis_expiry_seconds": 3600,  # 1 hour
        "last_time_redis_expiry_seconds": 3600,  # 1 hour
        # Global Limit
        "global_limit_count": 1000,
        "global_redis_expiry_seconds": 60,  # 1 minute
    },
    # Add other limit types here as needed
}
# --- End Rate Limiter Constants ---


logger = get_logger(__name__)

logger.debug("ENVIRONMENT is %s", os.getenv("ENVIRONMENT"))
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") != ENVIRONMENT.TEST.value,
)
logger.debug("Limiter enabled status: %s", limiter.enabled)


class CustomRateLimiter:
    """A modular and extensible rate limiter using Redis."""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client._instance  # Access the coredis client directly

    def _get_redis_key(
        self, limit_type: str, sub_key: str, identifier: str | None = None
    ) -> str:
        # Construct the key using the base prefix, limit type, sub_key, and optional identifier
        if identifier:
            return f"{RATE_LIMIT_BASE_PREFIX}{limit_type}:{sub_key}:{identifier}"
        return f"{RATE_LIMIT_BASE_PREFIX}{limit_type}:{sub_key}"

    async def _check_email_limit(
        self, email: str, config: Dict[str, Any], limit_type: str
    ) -> Tuple[bool, str | None]:
        """Sliding window: check email limit based on config."""
        key = self._get_redis_key(limit_type, SUB_KEY_EMAIL, email)
        now = time.time()
        hour_ago = now - config["email_limit_window_seconds"]

        await self.redis.zremrangebyscore(key, 0, hour_ago)
        count = await self.redis.zcard(key)

        if count >= config["email_limit_count"]:
            return (
                False,
                f"Maximum {config['email_limit_count']} OTP requests per hour for this email",
            )

        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, config["email_redis_expiry_seconds"])
        return True, None

    async def _check_ip_limit(
        self, ip: str, config: Dict[str, Any], limit_type: str
    ) -> Tuple[bool, str | None, int | None]:
        """Token bucket: check IP limit based on config."""
        key = self._get_redis_key(limit_type, SUB_KEY_IP, ip)
        now = time.time()
        capacity = config["ip_capacity"]
        refill_rate = config["ip_refill_rate_per_second"]

        data = await self.redis.hgetall(key)

        if not data:
            await self.redis.hset(
                key, mapping={"tokens": capacity - 1, "last_update": now}
            )
            await self.redis.expire(key, config["ip_redis_expiry_seconds"])
            return True, None, None

        tokens = float(data.get("tokens", "0"))
        last_update = float(data.get("last_update", "0"))

        elapsed = now - last_update
        tokens = min(capacity, tokens + (elapsed * refill_rate))

        if tokens < 1:
            retry_after = int((1 - tokens) / refill_rate)
            return (
                False,
                f"Too many requests from this IP. Retry after {retry_after} seconds",
                retry_after,
            )

        await self.redis.hset(key, mapping={"tokens": tokens - 1, "last_update": now})

        return True, None, None

    async def _check_progressive_delay(
        self, email: str, config: Dict[str, Any], limit_type: str
    ) -> Tuple[bool, str | None, int | None]:
        """Progressive delays based on attempts and config."""
        attempts_key = self._get_redis_key(limit_type, SUB_KEY_ATTEMPTS, email)
        last_time_key = self._get_redis_key(limit_type, SUB_KEY_LAST, email)

        attempts = await self.redis.incr(attempts_key)
        if attempts == 1:
            await self.redis.expire(
                attempts_key, config["attempts_redis_expiry_seconds"]
            )

        delays = config["progressive_delays"]
        required_delay = delays.get(attempts, 900)

        if required_delay > 0:
            last_time = await self.redis.get(last_time_key)
            if last_time:
                elapsed = time.time() - float(last_time)
                if elapsed < required_delay:
                    remaining = int(required_delay - elapsed)
                    return False, f"Please wait {remaining} seconds", attempts

        await self.redis.set(
            last_time_key, time.time(), ex=config["last_time_redis_expiry_seconds"]
        )
        return True, None, attempts

    async def _check_global_limit(
        self, config: Dict[str, Any], limit_type: str
    ) -> Tuple[bool, str | None]:
        """Global limit check based on config."""
        key = self._get_redis_key(limit_type, SUB_KEY_GLOBAL)
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, config["global_redis_expiry_seconds"])

        if count > config["global_limit_count"]:
            return False, "System is experiencing high load"

        return True, None

    async def check_limit(
        self, limit_type: str, request: Request, email: str
    ) -> Tuple[bool, str | None, int | None, int | None]:
        """
        Main method to check various rate limits based on type.
        """
        config = RATE_LIMIT_CONFIGS.get(limit_type)
        if not config:
            logger.error(
                f"Rate limiter: Configuration not found for limit_type: {limit_type}"
            )
            return False, "Rate limiter configuration error", None, None

        # Pass config to sub-check methods
        ip = get_remote_address(request)
        ip_retry_after: int | None = None

        allowed, error = await self._check_email_limit(email, config, limit_type)
        if not allowed:
            return False, error, None, ip_retry_after

        allowed, error, ip_retry_after = await self._check_ip_limit(
            ip, config, limit_type
        )
        if not allowed:
            return False, error, None, ip_retry_after

        allowed, error, attempts = await self._check_progressive_delay(
            email, config, limit_type
        )
        if not allowed:
            return False, error, attempts, ip_retry_after

        allowed, error = await self._check_global_limit(config, limit_type)
        if not allowed:
            return False, error, None, ip_retry_after

        return True, None, attempts, ip_retry_after


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
                email=identifier_value,
            )

            if not allowed:
                detail = {"message": error_msg}
                if attempts is not None:
                    detail["attempt"] = attempts

                headers = {}
                if retry_after_value is not None:
                    headers["Retry-After"] = str(
                        retry_after_value
                    )  # Add Retry-After header

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=detail,
                    headers=headers,  # Pass headers
                )

            return await func(request, custom_limiter, *args, **kwargs)

        return wrapper_function

    return wrapper_decorator


def add_rate_limiter(app: FastAPI):
    if os.getenv("ENVIRONMENT") == ENVIRONMENT.TEST.value:
        return
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

