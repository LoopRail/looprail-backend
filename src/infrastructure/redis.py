import json
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from coredis import Redis
from coredis.exceptions import RedisError

from src.infrastructure.settings import RedisConfig
from src.types import Error, error

T = TypeVar("T")

TTL = 60 * 1000  # milliseconds


async def _create_client(settings: RedisConfig):
    """Initialize Redis connection."""
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username,
        password=settings.redis_password,
        decode_responses=True,
    )
    return client


async def _serialize_data(data: Any) -> Tuple[str | None, Error | None]:
    """Serialize data to a JSON string."""
    if isinstance(data, str):
        return data, None
    if isinstance(data, (int, float)):
        return str(data), None
    if (
        isinstance(data, dict)
        or hasattr(data, "model_dump_json")
        or hasattr(data, "dict")
    ):
        if hasattr(data, "model_dump_json"):
            return str(data.model_dump_json()), None
        if hasattr(data, "dict"):
            return str(data.dict()), None
        return str(json.dumps(data)), None
    return None, error(
        "Data must be a serializable type (dict, Pydantic model, str, int, float)"
    )


class RedisTransaction:
    def __init__(self, client: Redis):
        self._pipe = client.pipeline(transaction=True)

    def create(
        self, key: str, data: Any, ttl: int = TTL
    ) -> Tuple[Optional["RedisTransaction"], Error]:
        """Queue a create operation in the transaction."""
        serialized_data, err = _serialize_data(data)
        if err:
            return None, err
        self._pipe.set(key, serialized_data, ex=ttl)
        return self, None

    def update(self, key: str, data: Any) -> "RedisTransaction":
        """Queue an update operation in the transaction."""
        return self.create(key, data)

    def delete(self, key: str) -> "RedisTransaction":
        """Queue a delete operation in the transaction."""
        self._pipe.delete(key)
        return self

    async def commit(self) -> Error | None:
        """Execute all queued operations in the transaction."""
        try:
            await self._pipe.execute()
            return None
        except RedisError as e:
            return error(f"Transaction failed: {e}")


class RedisClient:
    def __init__(self, settings: RedisConfig):
        self._instance = _create_client(settings)

    def transaction(self) -> RedisTransaction:
        """Start a new transaction."""
        return RedisTransaction(self._instance)

    async def create(self, key: str, data: Any, ttl: int = TTL) -> Error:
        """Create a new object in Redis."""
        serialized_data, err = _serialize_data(data)
        if err:
            return err
        success = await self._instance.set(key, serialized_data, ex=ttl)
        return error("Could not upload to redis") if not success else None

    async def batch_create(self, items: Dict[str, Any]) -> List[bool]:
        """Create multiple objects in a batch operation."""
        pipe = self._instance.pipeline()
        for key, data in items.items():
            serialized_data, err = _serialize_data(data)
            if not err:
                pipe.set(key, serialized_data, ex=TTL)
        return await pipe.execute()

    async def get(
        self, key: str, object_class: Type[T] = None
    ) -> Tuple[Optional[T], Error]:
        """Retrieve an object from Redis."""
        data = await self._instance.get(key)
        if data is None:
            return None, error("Not found")
        try:
            deserialized_data = json.loads(data)
            if object_class:
                return object_class(**deserialized_data), None
            return deserialized_data, None
        except json.JSONDecodeError:
            if object_class and issubclass(object_class, str):
                return data, None
            return data, None

    async def get_many(
        self, keys: List[str], object_class: Type[T] = None
    ) -> List[Optional[T]]:
        """Retrieve multiple objects from Redis."""
        pipe = self._instance.pipeline()
        for key in keys:
            pipe.get(key)
        results = await pipe.execute()
        objects = []
        for data in results:
            if data is None:
                objects.append(None)
            else:
                try:
                    deserialized_data = json.loads(data)
                    if object_class:
                        objects.append(object_class(**deserialized_data))
                    else:
                        objects.append(deserialized_data)
                except json.JSONDecodeError:
                    if object_class and issubclass(object_class, str):
                        objects.append(data)
                    else:
                        objects.append(data)
        return objects

    async def get_all(
        self, pattern: str = "*", object_class: Type[T] = None
    ) -> List[T]:
        """Retrieve all objects matching a pattern."""
        keys = await self._instance.keys(pattern)
        return await self.get_many(keys, object_class) if keys else []

    async def update(self, key: str, data: Any) -> error:
        """Update an existing object in Redis."""
        return await self.create(key, data)

    async def batch_update(self, items: Dict[str, Any]) -> List[bool]:
        """Update multiple objects in a batch operation."""
        return await self.batch_create(items)

    async def delete(self, key: str) -> bool:
        """Delete an object from Redis."""
        deleted_count = await self._instance.delete(key)
        return deleted_count > 0

    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple objects from Redis."""
        if not keys:
            return 0
        return await self._instance.delete(*keys)

    async def delete_all(self, pattern: str = "*") -> int:
        """Delete all objects matching a pattern."""
        keys = await self._instance.keys(pattern)
        if not keys:
            return 0
        return await self._instance.delete(*keys)

