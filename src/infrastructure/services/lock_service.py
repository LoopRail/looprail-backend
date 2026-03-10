import logging
import uuid
import time
import asyncio
from typing import Dict, Optional, Tuple

from src.infrastructure.redis import RedisClient
from src.types import error
from src.types.error import Error

logger = logging.getLogger(__name__)


class Lock:
    """Represents a single Redis-backed lock."""

    def __init__(
        self, redis_client: RedisClient, key_prefix: str, ttl_seconds: int = 30
    ):
        self.redis_client = redis_client
        self.prefix = f"lock:{key_prefix}:"
        self.ttl_seconds = ttl_seconds

    async def _get_key(self, key_id: str) -> str:
        return f"{self.prefix}{key_id}"

    async def acquire(
        self, key_id: str, blocking_timeout_seconds: int = 0
    ) -> Tuple[Optional[str], Error]:
        key = await self._get_key(key_id)
        lock_value = str(uuid.uuid4())

        logger.debug(
            "Attempting to acquire lock: key='%s', value='%s', timeout=%s",
            key,
            lock_value,
            blocking_timeout_seconds,
        )

        start_time = time.time()
        while True:
            err = await self.redis_client.create(key, lock_value, ttl=self.ttl_seconds)
            if not err:
                # Successfully acquired lock
                logger.info("Lock acquired for key='%s', value='%s'", key, lock_value)
                return lock_value, None

            # If no blocking timeout, or timeout has been reached, return the error
            elapsed = time.time() - start_time
            if blocking_timeout_seconds <= 0 or elapsed >= blocking_timeout_seconds:
                logger.info(
                    "Lock already held for key='%s' (waited %s seconds)",
                    key,
                    round(elapsed, 2),
                )
                return None, err

            # Otherwise, wait briefly and try again
            await asyncio.sleep(0.5)

    async def _get_state_key(self, key_id: str) -> str:
        return f"{self.prefix}{key_id}:state"

    async def set_state(self, key_id: str, state: str, ttl: int = None) -> Error:
        """
        Store arbitrary state associated with a lock key in Redis.
        State is kept independently of the lock ownership value so it
        survives across lock acquire / release cycles.
        """
        state_key = await self._get_state_key(key_id)
        effective_ttl = ttl if ttl is not None else self.ttl_seconds * 10
        err = await self.redis_client.update(state_key, state)
        if err:
            # update calls create which uses SET; retry with create
            err = await self.redis_client.create(state_key, state, ttl=effective_ttl)
        return err

    async def get_state(self, key_id: str) -> Tuple[Optional[str], Error]:
        """
        Read the state stored for a lock key without acquiring the lock.
        Returns (state_value, None) on success or (None, Error) if missing.
        """
        state_key = await self._get_state_key(key_id)
        value, err = await self.redis_client.get(state_key, str)
        return value, err

    async def release(self, key_id: str, lock_value: str) -> Error:
        key = await self._get_key(key_id)
        logger.debug("Releasing lock: key='%s', expected_value='%s'", key, lock_value)

        current_value, err = await self.redis_client.get(key, uuid.UUID)
        if err:
            return err
        if current_value != lock_value:
            logger.warning(
                "Cannot release lock for key='%s': current_value='%s' does not match expected",
                key,
                current_value,
            )
            return error("Lock ownership mismatch")

        ok = await self.redis_client.delete([key])
        if not ok:
            logger.error("Failed to delete lock key='%s'", key)
            return error("Failed to delete key")

        logger.info("Lock released for key='%s', value='%s'", key, lock_value)
        return None


class LockService:
    """
    Registry for locks: returns a Lock instance per logical category (e.g., deposits, withdrawals)
    """

    def __init__(self, redis_client: RedisClient, ttl_seconds: int = 30):
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self._locks: Dict[str, Lock] = {}

    def get(self, lock_name: str) -> Lock:
        """
        Returns a Lock object for the given name.
        Creates a new Lock if it does not exist yet.
        """
        if lock_name not in self._locks:
            logger.debug("Creating new lock instance for '%s'", lock_name)
            self._locks[lock_name] = Lock(
                self.redis_client, key_prefix=lock_name, ttl_seconds=self.ttl_seconds
            )
        return self._locks[lock_name]
