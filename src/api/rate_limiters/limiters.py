import os
import time

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.infrastructure import RedisClient, get_logger
from src.infrastructure.settings import ENVIRONMENT

from dataclasses import dataclass, field
from typing import Dict

logger = get_logger(__name__)

logger.debug("ENVIRONMENT is %s", os.getenv("ENVIRONMENT"))

# --- Rate Limiter Constants ---
# Redis Key Prefixes
EMAIL_RATE_LIMIT_KEY_PREFIX = "rate-limit:{subject}:email:"
IP_RATE_LIMIT_KEY_PREFIX = "rate-limit:{subject}:ip:"
ATTEMPTS_KEY_PREFIX = "rate-limit:{subject}:attempts:"
LAST_TIME_KEY_PREFIX = "rate-limit:{subject}:last:"
GLOBAL_RATE_LIMIT_KEY = "rate-limit:{subject}:global"


@dataclass
class EmailRateLimitConfig:
    count: int
    window_seconds: int
    redis_expiry_seconds: int


@dataclass
class IpRateLimitConfig:
    capacity: int
    refill_rate_per_hour: int
    refill_rate_per_second: float = field(init=False)
    redis_expiry_seconds: int

    def __post_init__(self):
        self.refill_rate_per_second = self.refill_rate_per_hour / 3600


@dataclass
class ProgressiveDelayConfig:
    attempts_redis_expiry_seconds: int
    last_time_redis_expiry_seconds: int
    delays: Dict[int, int] = field(default_factory=dict)


@dataclass
class GlobalRateLimitConfig:
    count: int
    redis_expiry_seconds: int


@dataclass
class RateLimitSubjectConfig:
    email: EmailRateLimitConfig
    ip: IpRateLimitConfig
    progressive_delay: ProgressiveDelayConfig
    global_limit: GlobalRateLimitConfig


RATE_LIMIT_CONFIG: Dict[str, RateLimitSubjectConfig] = {
    "otp": RateLimitSubjectConfig(
        email=EmailRateLimitConfig(
            count=5,
            window_seconds=3600,
            redis_expiry_seconds=7200,
        ),
        ip=IpRateLimitConfig(
            capacity=20,
            refill_rate_per_hour=10,
            redis_expiry_seconds=7200,
        ),
        progressive_delay=ProgressiveDelayConfig(
            delays={1: 0, 2: 0, 3: 30, 4: 120, 5: 900},
            attempts_redis_expiry_seconds=3600,
            last_time_redis_expiry_seconds=3600,
        ),
        global_limit=GlobalRateLimitConfig(
            count=1000,
            redis_expiry_seconds=60,
        ),
    ),
    "withdrawal": RateLimitSubjectConfig(
        email=EmailRateLimitConfig(
            count=10,
            window_seconds=3600,
            redis_expiry_seconds=7200,
        ),
        ip=IpRateLimitConfig(
            capacity=40,
            refill_rate_per_hour=20,
            redis_expiry_seconds=7200,
        ),
        progressive_delay=ProgressiveDelayConfig(
            delays={1: 0, 2: 0, 3: 30, 4: 120, 5: 900},
            attempts_redis_expiry_seconds=3600,
            last_time_redis_expiry_seconds=3600,
        ),
        global_limit=GlobalRateLimitConfig(
            count=2000,
            redis_expiry_seconds=60,
        ),
    ),
}


limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") != ENVIRONMENT.TEST.value,
)
logger.debug("Limiter enabled status: %s", limiter.enabled)


class CustomRateLimiter:
    """A modular and extensible rate limiter using Redis."""

    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client._instance  # Access the coredis client directly

    async def _check_email_limit(
        self, subject: str, email: str
    ) -> tuple[bool, str | None]:
        """Sliding window: Configurable requests per hour for an email"""
        config = RATE_LIMIT_CONFIG.get(subject)
        if not config:
            logger.warning(
                "Rate limit configuration not found for subject: %s", subject
            )
            return True, None  # Allow by default if config is missing

        limit_config = config.email
        limit_count = limit_config.count
        limit_window_seconds = limit_config.window_seconds
        redis_expiry_seconds = limit_config.redis_expiry_seconds

        key = f"{EMAIL_RATE_LIMIT_KEY_PREFIX.format(subject=subject)}{email}"
        now = time.time()
        window_start = now - limit_window_seconds

        await self.redis.zremrangebyscore(key, 0, window_start)
        count = await self.redis.zcard(key)

        if count >= limit_count:
            return (
                False,
                f"Maximum {limit_count} requests per hour for this email",
            )

        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, redis_expiry_seconds)
        return True, None

    async def _check_ip_limit(
        self, subject: str, ip: str
    ) -> tuple[bool, str | None, int | None]:
        """Token bucket: Configurable capacity and refill rate for an IP"""
        config = RATE_LIMIT_CONFIG.get(subject)
        if not config:
            logger.warning(
                "Rate limit configuration not found for subject: %s", subject
            )
            return True, None, None  # Allow by default if config is missing

        limit_config = config.ip
        capacity = limit_config.capacity
        refill_rate = limit_config.refill_rate_per_second
        redis_expiry_seconds = limit_config.redis_expiry_seconds

        key = f"{IP_RATE_LIMIT_KEY_PREFIX.format(subject=subject)}{ip}"
        now = time.time()

        data = await self.redis.hgetall(key)

        if not data:
            await self.redis.hset(
                key, field_values={"tokens": capacity - 1, "last_update": now}
            )
            await self.redis.expire(key, redis_expiry_seconds)
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

        await self.redis.hset(
            key, field_values={"tokens": tokens - 1, "last_update": now}
        )

        return True, None, None

    async def _check_progressive_delay(
        self, subject: str, email: str
    ) -> tuple[bool, str | None, int | None]:
        """Progressive delays based on attempts."""
        config = RATE_LIMIT_CONFIG.get(subject)
        if not config:
            logger.warning(
                "Rate limit configuration not found for subject: %s", subject
            )
            return True, None, None  # Allow by default if config is missing

        limit_config = config.progressive_delay
        delays = limit_config.delays
        attempts_redis_expiry_seconds = limit_config.attempts_redis_expiry_seconds
        last_time_redis_expiry_seconds = limit_config.last_time_redis_expiry_seconds

        attempts_key = f"{ATTEMPTS_KEY_PREFIX.format(subject=subject)}{email}"
        last_time_key = f"{LAST_TIME_KEY_PREFIX.format(subject=subject)}{email}"

        attempts = await self.redis.incr(attempts_key)
        if attempts == 1:
            await self.redis.expire(attempts_key, attempts_redis_expiry_seconds)

        required_delay = delays.get(attempts, 900)

        if required_delay > 0:
            last_time = await self.redis.get(last_time_key)
            if last_time:
                elapsed = time.time() - float(last_time)
                if elapsed < required_delay:
                    remaining = int(required_delay - elapsed)
                    return False, f"Please wait {remaining} seconds", attempts

        await self.redis.set(
            last_time_key, time.time(), ex=last_time_redis_expiry_seconds
        )
        return True, None, attempts

    async def _check_global_limit(self, subject: str) -> tuple[bool, str | None]:
        """Global: Configurable requests per minute."""
        config = RATE_LIMIT_CONFIG.get(subject)
        if not config:
            logger.warning(
                "Rate limit configuration not found for subject: %s", subject
            )
            return True, None  # Allow by default if config is missing

        limit_config = config.global_limit
        limit_count = limit_config.count
        redis_expiry_seconds = limit_config.redis_expiry_seconds

        key = GLOBAL_RATE_LIMIT_KEY.format(subject=subject)
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, redis_expiry_seconds)

        if count > limit_count:
            return False, "System is experiencing high load"

        return True, None

    async def check_limit(
        self, limit_type: str, request: Request, identifier_value
    ) -> tuple[bool, str | None, int | None, int | None]:
        """
        Main method to check various rate limits based on type.
        """
        ip = get_remote_address(request)
        ip_retry_after: int | None = None

        allowed, error = await self._check_email_limit(limit_type, identifier_value)
        if not allowed:
            return False, error, None, ip_retry_after

        allowed, error, ip_retry_after = await self._check_ip_limit(limit_type, ip)
        if not allowed:
            return False, error, None, ip_retry_after

        allowed, error, attempts = await self._check_progressive_delay(
            limit_type, identifier_value
        )
        if not allowed:
            return False, error, attempts, ip_retry_after

        allowed, error = await self._check_global_limit(limit_type)
        if not allowed:
            return False, error, None, ip_retry_after

        return True, None, attempts, ip_retry_after
