import os
import time

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.infrastructure import RedisClient, get_logger
from src.infrastructure.settings import ENVIRONMENT

# --- Rate Limiter Constants ---
# Redis Key Prefixes
EMAIL_RATE_LIMIT_KEY_PREFIX = "rate-limit:{subject}:email:"
IP_RATE_LIMIT_KEY_PREFIX = "rate-limit:{subject}:ip:"
ATTEMPTS_KEY_PREFIX = "rate-limit:{subject}:attempts:"
LAST_TIME_KEY_PREFIX = "rate-limit:{subject}:last:"
GLOBAL_RATE_LIMIT_KEY = "rate-limit:{subject}:global"


# Email Limit (Sliding Window)
OTP_EMAIL_LIMIT_COUNT = 5
OTP_EMAIL_LIMIT_WINDOW_SECONDS = 3600  # 1 hour
OTP_EMAIL_REDIS_EXPIRY_SECONDS = 7200  # 2 hours

# IP Limit (Token Bucket)
OTP_IP_CAPACITY = 20
OTP_IP_REFILL_RATE_PER_HOUR = 10
OTP_IP_REFILL_RATE_PER_SECOND = OTP_IP_REFILL_RATE_PER_HOUR / 3600
OTP_IP_REDIS_EXPIRY_SECONDS = 7200  # 2 hours

# Progressive Delay
OTP_PROGRESSIVE_DELAYS = {1: 0, 2: 0, 3: 30, 4: 120, 5: 900}
OTP_ATTEMPTS_REDIS_EXPIRY_SECONDS = 3600  # 1 hour
OTP_LAST_TIME_REDIS_EXPIRY_SECONDS = 3600  # 1 hour

# Global Limit
OTP_GLOBAL_LIMIT_COUNT = 1000
OTP_GLOBAL_REDIS_EXPIRY_SECONDS = 60  # 1 minute
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

    async def _check_email_limit(
        self, subject: str, email: str
    ) -> tuple[bool, str | None]:
        """Sliding window: 5 OTPs per hour for a email"""
        key = f"{EMAIL_RATE_LIMIT_KEY_PREFIX.format(subject=subject)}{email}"
        now = time.time()
        hour_ago = now - OTP_EMAIL_LIMIT_WINDOW_SECONDS

        # Use coredis commands
        await self.redis.zremrangebyscore(key, 0, hour_ago)
        count = await self.redis.zcard(key)

        if count >= OTP_EMAIL_LIMIT_COUNT:
            return (
                False,
                f"Maximum {OTP_EMAIL_LIMIT_COUNT} OTP requests per hour for this email",
            )

        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, OTP_EMAIL_REDIS_EXPIRY_SECONDS)
        return True, None

    async def _check_ip_limit(
        self, subject: str, ip: str
    ) -> tuple[bool, str | None, int | None]:
        """Token bucket: 20 capacity, 10 per hour refill."""
        key = f"{IP_RATE_LIMIT_KEY_PREFIX.format(subject=subject)}{ip}"
        now = time.time()
        capacity = OTP_IP_CAPACITY
        refill_rate = OTP_IP_REFILL_RATE_PER_SECOND

        # Use coredis commands
        data = await self.redis.hgetall(key)

        if not data:
            await self.redis.hset(
                key, mapping={"tokens": capacity - 1, "last_update": now}
            )
            await self.redis.expire(key, OTP_IP_REDIS_EXPIRY_SECONDS)
            return True, None, None

        tokens = float(data.get("tokens", "0"))  # Handle potential missing key
        last_update = float(
            data.get("last_update", "0")
        )  # Handle potential missing key

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
        self, subject: str, email: str
    ) -> tuple[bool, str | None, int | None]:
        """Progressive delays based on attempts."""
        attempts_key = f"{ATTEMPTS_KEY_PREFIX.format(subject=subject)}{email}"
        last_time_key = f"{LAST_TIME_KEY_PREFIX.format(subject=subject)}{email}"

        # Use coredis commands for incr and get
        attempts = await self.redis.incr(attempts_key)
        if attempts == 1:
            await self.redis.expire(attempts_key, OTP_ATTEMPTS_REDIS_EXPIRY_SECONDS)

        delays = OTP_PROGRESSIVE_DELAYS
        required_delay = delays.get(attempts, 900)

        if required_delay > 0:
            last_time = await self.redis.get(last_time_key)
            if last_time:
                elapsed = time.time() - float(last_time)
                if elapsed < required_delay:
                    remaining = int(required_delay - elapsed)
                    return False, f"Please wait {remaining} seconds", attempts

        await self.redis.set(
            last_time_key, time.time(), ex=OTP_LAST_TIME_REDIS_EXPIRY_SECONDS
        )
        return True, None, attempts

    async def _check_global_limit(self, subject: str) -> tuple[bool, str | None]:
        """Global: 1000 OTPs per minute."""
        key = GLOBAL_RATE_LIMIT_KEY.format(subject=subject)
        # Use coredis commands for incr and expire
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, OTP_GLOBAL_REDIS_EXPIRY_SECONDS)

        if count > OTP_GLOBAL_LIMIT_COUNT:
            return False, "System is experiencing high load"

        return True, None

    async def check_limit(
        self, limit_type: str, request: Request, identifier_value
    ) -> tuple[bool, str | None, int | None, int | None]:
        """
        Main method to check various rate limits based on type.
        kwargs can include 'email'.
        """
        if limit_type == "otp":
            ip = get_remote_address(request)
            ip_retry_after: int | None = None

            allowed, error = await self._check_email_limit("otp", identifier_value)
            if not allowed:
                return False, error, None, ip_retry_after

            allowed, error, ip_retry_after = await self._check_ip_limit("otp", ip)
            if not allowed:
                return False, error, None, ip_retry_after

            allowed, error, attempts = await self._check_progressive_delay(
                "otp", identifier_value
            )
            if not allowed:
                return False, error, attempts, ip_retry_after

            allowed, error = await self._check_global_limit("otp")
            if not allowed:
                return False, error, None, ip_retry_after

            return True, None, attempts, ip_retry_after

        return True, None, None, None
