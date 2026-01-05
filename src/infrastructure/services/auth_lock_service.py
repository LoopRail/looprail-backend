import json
from datetime import datetime, timedelta
from typing import Optional, Tuple

from src.infrastructure.redis import RedisClient
from src.infrastructure.constants import (
    ACCOUNT_LOCKOUT_DURATION_MINUTES,
    MAX_FAILED_OTP_ATTEMPTS,
)
from src.types import Error, FailedAttemptError, LockedAccount


class AuthLockService:
    """Service to track and manage failed authentication attempts for account locking."""

    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.prefix = "auth_lock:"

    async def _get_key(self, user_email: str) -> str:
        """Generates the Redis key for a given user email."""
        return f"{self.prefix}{user_email}"

    async def increment_failed_attempts(
        self, user_email: str
    ) -> Tuple[int, Optional[Error]]:
        """Increments the failed attempt count for a user.

        If the count exceeds MAX_FAILED_OTP_ATTEMPTS, the account is locked.
        """
        key = await self._get_key(user_email)
        current_attempts = await self.redis_client.incr(key)

        if current_attempts == 1:
            await self.redis_client.expire(
                key, timedelta(minutes=ACCOUNT_LOCKOUT_DURATION_MINUTES)
            )

        if current_attempts >= MAX_FAILED_OTP_ATTEMPTS:
            await self.lock_account(user_email)
            return current_attempts, FailedAttemptError(
                "Account locked due to too many failed attempts."
            )

        return current_attempts, None

    async def reset_failed_attempts(self, user_email: str) -> Optional[Error]:
        """Resets the failed attempt count for a user."""
        key = await self._get_key(user_email)
        await self.redis_client.delete(key)
        return None

    async def get_failed_attempts(self, user_email: str) -> Tuple[int | None, Error]:
        """Retrieves the current failed attempt count for a user."""
        key = await self._get_key(user_email)
        attempts, err = await self.redis_client.get(key, LockedAccount)
        if err:
            return None, err
        return int(attempts) if attempts else 0, None

    async def lock_account(
        self, user_email: str, duration_minutes: Optional[int] = None
    ) -> Optional[Error]:
        """Locks a user's account by setting a lockout key."""
        lock_duration = duration_minutes or ACCOUNT_LOCKOUT_DURATION_MINUTES
        key = await self._get_key(user_email)
        # Store lockout timestamp to indicate when the lock expires
        lock_data = {"locked_at": datetime.utcnow().isoformat()}
        await self.redis_client.set(
            key, json.dumps(lock_data), ex=timedelta(minutes=lock_duration)
        )
        return None

    async def is_account_locked(self, user_email: str) -> Tuple[bool, Optional[Error]]:
        """Checks if a user's account is currently locked."""
        key = await self._get_key(user_email)
        lock_data_raw = await self.redis_client.get(key)
        if lock_data_raw:
            try:

                # If there's a lock_data and it was set, consider it locked.
                # Redis `ex` (expire) handles the duration automatically.
                return True, FailedAttemptError(
                    f"Account is locked. Try again after {ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes."
                )
            except json.JSONDecodeError:
                # If the value is not JSON (e.g., just the attempt counter),
                # it means it's still tracking attempts, not locked yet.
                pass
        return False, None


# TODO add account locking
