import logging
import uuid
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

    async def acquire(self, key_id: str) -> Tuple[Optional[str], Error]:
        key = await self._get_key(key_id)
        lock_value = str(uuid.uuid4())

        logger.debug(
            "Attempting to acquire lock: key='%s', value='%s'", key, lock_value
        )
        err = await self.redis_client.create(key, lock_value, ex=self.ttl_seconds)
        if err:
            logger.info("Lock already held for key='%s'", key)
            return None, err

        logger.info("Lock acquired for key='%s', value='%s'", key, lock_value)
        return lock_value, None

    async def release(self, key_id: str, lock_value: str) -> Error:
        key = await self._get_key(key_id)
        logger.debug("Releasing lock: key='%s', expected_value='%s'", key, lock_value)

        current_value = await self.redis_client.get(key, uuid.UUID)
        if current_value != lock_value:
            logger.warning(
                "Cannot release lock for key='%s': current_value='%s' does not match expected",
                key,
                current_value,
            )
            return error("Lock ownership mismatch")

        err = await self.redis_client.delete([key])
        if err:
            logger.error("Failed to delete lock key='%s': %s", key, err)
            return err

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
