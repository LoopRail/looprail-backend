import json
from typing import Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RedisClient
from src.types.error import Error

T = TypeVar("T", bound=BaseModel)

logger = get_logger(__name__)


class CacheService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        logger.debug("CacheService initialized")

    def _get_key(self, prefix: str, identifier: Union[str, int]) -> str:
        return f"{prefix}:{identifier}"

    async def get(
        self,
        prefix: str,
        identifier: Union[str, int],
        model_class: Optional[Type[T]] = None,
    ) -> Optional[Union[T, dict]]:
        key = self._get_key(prefix, identifier)
        logger.debug("Attempting to get object from cache: %s", key)

        data, err = await self.redis.get(key)
        if err or not data:
            if err:
                logger.warning("Error fetching key %s from redis: %s", key, err.message)
            return None

        try:
            # Redis class might already return a dict if it was JSON serializable
            if isinstance(data, str):
                data = json.loads(data)

            if model_class:
                return model_class.model_validate(data)
            return data
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(
                "Failed to deserialize cached object for key %s: %s", key, str(e)
            )
            # Optional: delete corrupted cache
            await self.delete(prefix, identifier)
            return None

    async def set(
        self,
        prefix: str,
        identifier: Union[str, int],
        obj: Union[T, dict],
        ttl_seconds: int = 3600,
    ) -> Error:
        key = self._get_key(prefix, identifier)
        logger.debug("Setting object in cache: %s with TTL %ds", key, ttl_seconds)

        # If it's a Pydantic model, convert to dict with JSON-compatible types
        if hasattr(obj, "model_dump"):
            try:
                data = obj.model_dump(mode="json")
            except TypeError:
                # Fallback for Pydantic v1 or if mode='json' is not supported
                data = obj.dict() if hasattr(obj, "dict") else obj
        else:
            data = obj

        return await self.redis.create(key, data, ttl=ttl_seconds * 1000)

    async def delete(self, prefix: str, identifier: Union[str, int]) -> bool:
        key = self._get_key(prefix, identifier)
        logger.debug("Deleting object from cache: %s", key)
        return await self.redis.delete([key])

    async def clear_prefix(self, prefix: str) -> int:
        pattern = f"{prefix}:*"
        logger.debug("Clearing cache with pattern: %s", pattern)
        return await self.redis.delete_all(pattern)
