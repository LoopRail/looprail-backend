import json
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from coredis import Redis

from src.infrastructure.settings import RedisConfig
from src.types import Error, error

T = TypeVar("T")

TTL = 60 * 1000  # milliseconds


def _create_client(settings: RedisConfig):
    """Initialize Redis connection."""
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username,
        password=settings.redis_password,
        decode_responses=True,  # Ensures Redis returns strings instead of bytes
    )
    return client


class RedisClient:
    def __init__(self, settings: RedisConfig):
        self._instance = _create_client(settings)

    async def create(self, key: str, data: Any) -> Error:
        """
        Create a new object in Redis.

        Args:
            key: The unique identifier/key for the object
            data: The data to store (will be JSON serialized)

        Returns:
            Tuple[bool, error]: Tuple containing success status and error (if any)
        """
        if (
            isinstance(data, dict)
            or hasattr(data, "model_dump_json")
            or hasattr(data, "dict")
        ):
            if hasattr(data, "model_dump_json"):
                serialized_data = str(data.model_dump_json())
            elif hasattr(data, "dict"):
                serialized_data = str(data.dict())
            else:
                serialized_data = str(json.dumps(data))
            success = await self._instance.set(key, serialized_data, ex=TTL)
            return error("Could not upload to redis") if not success else None
        return error(
            "Data must be a dictionary or have amodel_dump_json or dict method"
        )

    async def batch_create(self, items: Dict[str, Any]) -> List[bool]:
        """
        Create multiple objects in a batch operation.

        Args:
            items: Dictionary mapping keys to their data objects

        Returns:
            List[bool]: List of success results for each operation
        """
        pipe = self._instance.pipeline()

        for key, data in items.items():
            serialized_data = (
                data.model_dump_json()
                if hasattr(data, "model_dump_json")
                else json.dumps(data)
            )
            pipe.set(key, serialized_data, ex=TTL)

        return pipe.execute()

    async def get(
        self, key: str, object_class: Type[T] = None
    ) -> Tuple[Optional[T], Error]:
        """
        Retrieve an object from Redis.

        Args:
            key: The unique identifier/key for the object
            object_class: Optional class to deserialize the data into

        Returns:
            Tuple[Optional[T], error]: Tuple containing the get object (or None) and error (if any)
        """
        data = await self._instance.get(key)

        if data is None:
            return None, error("Not found")

        deserialized_data = json.loads(data)

        if object_class:
            return object_class(**deserialized_data), None
        return deserialized_data, None

    async def get_many(
        self, keys: List[str], object_class: Type[T] = None
    ) -> List[Optional[T]]:
        """
        Retrieve multiple objects from Redis.

        Args:
            keys: List of keys to get
            object_class: Optional class to deserialize the data into

        Returns:
            List[Optional[T]]: List of getd objects (None for keys that don't exist)
        """
        pipe = self._instance.pipeline()

        for key in keys:
            pipe.get(key)

        results = pipe.execute()
        objects = []

        for data in results:
            if data is None:
                objects.append(None)
            else:
                deserialized_data = json.loads(data)
                if object_class:
                    objects.append(object_class(**deserialized_data))
                else:
                    objects.append(deserialized_data)

        return objects

    async def get_all(
        self, pattern: str = "*", object_class: Type[T] = None
    ) -> List[T]:
        """
        Retrieve all objects matching a pattern.

        Args:
            pattern: Redis key pattern to match
            object_class: Optional class to deserialize the data into

        Returns:
            List[T]: List of get objects
        """
        keys = self._instance.keys(pattern)
        return await self.get_many(keys, object_class) if keys else []

    async def update(self, key: str, data: Any) -> error:
        """
        Update an existing object in Redis.

        Args:
            key: The unique identifier/key for the object
            data: The new data to store

        Returns:
            Tuple[bool, error]: Tuple containing success status and error (if any)
        """
        return await self.create(key, data)  # Using create since Redis SET replaces

    async def batch_update(self, items: Dict[str, Any]) -> List[bool]:
        """
        Update multiple objects in a batch operation.

        Args:
            items: Dictionary mapping keys to their updated data

        Returns:
            List[bool]: List of success results for each operation
        """
        return await self.batch_create(items)  # Same as batch create since SET replaces

    async def delete(self, key: str) -> bool:
        """
        Delete an object from Redis.

        Args:
            key: The unique identifier/key for the object

        Returns:
            bool: True if deletion was successful
        """
        deleted_count = self._instance.delete(key)
        return deleted_count > 0

    async def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple objects from Redis.

        Args:
            keys: List of keys to delete

        Returns:
            int: Number of objects successfully deleted
        """
        if not keys:
            return 0

        return await self._instance.delete(*keys)

    async def delete_all(self, pattern: str = "*") -> int:
        """
        Delete all objects matching a pattern.

        Args:
            pattern: Redis key pattern to match

        Returns:
            int: Number of objects deleted
        """
        keys = self._instance.keys(pattern)
        if not keys:
            return 0

        return await self._instance.delete(*keys)
