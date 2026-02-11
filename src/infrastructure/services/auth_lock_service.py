import json
from datetime import datetime, timedelta
from typing import Optional, Self, Tuple

from src.infrastructure.constants import (
    ACCOUNT_LOCKOUT_DURATION_MINUTES,
    MAX_FAILED_OTP_ATTEMPTS,
)
from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RedisClient
from src.types import Error, FailedAttemptError, LockedAccount
from src.types.error import NotFoundError

logger = get_logger(__name__)


class AuthLockService:
    """Service to track and manage failed authentication attempts for account locking."""

    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.prefix = "auth_lock"
        self.subject = None
        logger.debug("AuthLockService initialized with prefix: %s", self.prefix)

    def set_subject(self, subject: str) -> Self:
        self.subject = subject
        return self

    async def _get_key(self, user_email: str, purpose: str = "default") -> str:
        """Generates a Redis key for a given user email and purpose."""
        if self.subject:
            key = f"{self.prefix}:{self.subject}:{purpose}:{user_email}"
        else:
            key = f"{self.prefix}:{purpose}:{user_email}"

        logger.debug(
            "Generated Redis key for user %s (purpose=%s): %s",
            user_email,
            purpose,
            key,
        )
        return key

    async def increment_failed_attempts(
        self, user_email: str
    ) -> Tuple[int, Optional[Error]]:
        """Increments the failed attempt count for a user.

        If the count exceeds MAX_FAILED_OTP_ATTEMPTS, the account is locked.
        """
        logger.debug("Incrementing failed attempts for user: %s", user_email)
        key = await self._get_key(user_email, "failed_attempts")
        current_attempts = await self.redis_client._instance.incr(key)
        logger.debug(
            "User %s now has %s failed attempts.", user_email, current_attempts
        )

        if current_attempts == 1:
            logger.debug(
                "Setting expiry for user %s failed attempts key to %s minutes",
                user_email,
                ACCOUNT_LOCKOUT_DURATION_MINUTES,
            )
            await self.redis_client._instance.expire(
                key, timedelta(minutes=ACCOUNT_LOCKOUT_DURATION_MINUTES)
            )

        if current_attempts >= MAX_FAILED_OTP_ATTEMPTS:
            logger.info(
                "Account locked for user %s due to exceeding max failed attempts (%s)",
                user_email,
                MAX_FAILED_OTP_ATTEMPTS,
            )
            await self._lock_account(user_email)
            return current_attempts, FailedAttemptError(
                "Account locked due to too many failed attempts."
            )

        return current_attempts, None

    async def reset_failed_attempts(self, user_email: str) -> Optional[Error]:
        """Resets the failed attempt count for a user."""
        logger.debug("Resetting failed attempts for user: %s", user_email)
        key = await self._get_key(user_email, "failed_attempts")
        await self.redis_client.delete([key])
        logger.info("Failed attempts reset for user: %s", user_email)
        return None

    async def get_failed_attempts(self, user_email: str) -> Tuple[int | None, Error]:
        """Retrieves the current failed attempt count for a user."""
        logger.debug("Retrieving failed attempts for user: %s", user_email)
        key = await self._get_key(user_email, "failed_attempts")
        attempts, err = await self.redis_client.get(key, LockedAccount)
        if err:
            logger.error(
                "Error retrieving failed attempts for user %s: %s",
                user_email,
                err.message,
            )
            return None, err
        logger.debug(
            "User %s has %s failed attempts.", user_email, attempts if attempts else 0
        )
        return int(attempts) if attempts else 0, None

    async def _lock_account(
        self, user_email: str, duration_minutes: Optional[int] = None
    ) -> Optional[Error]:
        """Locks a user's account by setting a lockout key."""
        logger.debug(
            "Locking account for user %s for %s minutes",
            user_email,
            duration_minutes if duration_minutes else ACCOUNT_LOCKOUT_DURATION_MINUTES,
        )
        lock_duration = duration_minutes or ACCOUNT_LOCKOUT_DURATION_MINUTES
        key = await self._get_key(user_email, "account_lock")
        lock_data = {"locked_at": datetime.utcnow().isoformat()}
        await self.redis_client.create(
            key, json.dumps(lock_data), ttl=timedelta(minutes=lock_duration)
        )
        logger.info(
            "Account %s locked until: %s",
            user_email,
            datetime.utcnow() + timedelta(minutes=lock_duration),
        )
        return None

    async def is_account_locked(self, user_email: str) -> Tuple[bool, Optional[Error]]:
        """Checks if a user's account is currently locked."""
        logger.debug("Checking if account is locked for user: %s", user_email)
        key = await self._get_key(user_email, "account_lock")
        lock_data_raw, err = await self.redis_client.get(key)
        if err and err != NotFoundError:
            return True, err
        if lock_data_raw:
            logger.debug("Lock data found for user %s: %s", user_email, lock_data_raw)
            return True, FailedAttemptError(
                f"Account is locked. Try again after {ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes."
            )
        logger.debug("Account not locked for user: %s", user_email)
        return False, None
