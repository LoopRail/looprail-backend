import json
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from src.infrastructure.settings import RedisConfig
from src.types import Error, error

T = TypeVar("T")

TTL = 60 * 1000  # milliseconds

def _serialize_data(data: Any) -> Tuple[str | None, Error | None]:
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

class MockRedisTransaction:
    def __init__(self, store: Dict[str, str]):
        self._store = store
        self._operations = []

    @classmethod
    async def new(cls, client: Any): # client here will be MockRedisClient
        return cls(client._store)

    async def create(
        self, key: str, data: Any, ttl: int = TTL
    ) -> Tuple[Optional["MockRedisTransaction"], Error]:
        serialized_data, err = _serialize_data(data)
        if err:
            return None, err
        self._operations.append(("set", key, serialized_data))
        return self, None

    async def update(self, key: str, data: Any) -> "MockRedisTransaction":
        return await self.create(key, data)

    async def delete(self, key: str) -> "MockRedisTransaction":
        self._operations.append(("delete", key))
        return self

    async def commit(self) -> Error:
        try:
            for op, key, *args in self._operations:
                if op == "set":
                    self._store[key] = args[0]
                elif op == "delete":
                    if key in self._store:
                        del self._store[key]
            self._operations = []
            return None
        except Exception as e:
            return error(f"Transaction failed: {e}")


class MockRedisClient:
    def __init__(self, settings: RedisConfig = None):
        self._store: Dict[str, str] = {} # In-memory store for mock Redis

    async def transaction(self) -> MockRedisTransaction:
        return await MockRedisTransaction.new(self)

    async def create(self, key: str, data: Any, ttl: int = TTL) -> Error:
        serialized_data, err = _serialize_data(data)
        if err:
            return err
        self._store[key] = serialized_data
        return None

    async def batch_create(self, items: Dict[str, Any]) -> List[bool]:
        results = []
        for key, data in items.items():
            serialized_data, err = _serialize_data(data)
            if not err:
                self._store[key] = serialized_data
                results.append(True)
            else:
                results.append(False)
        return results

    async def get(
        self, key: str, object_class: Type[T] = None
    ) -> Tuple[Optional[T], Error]:
        data = self._store.get(key)
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
        except Exception as e:
            return None, error(f"Deserialization error: {e}")

    async def get_many(
        self, keys: List[str], object_class: Type[T] = None
    ) -> List[Optional[T]]:
        objects = []
        for key in keys:
            data = self._store.get(key)
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
                except Exception:
                    objects.append(None) # Append None if any other error occurs during deserialization
        return objects

    async def get_all(
        self, pattern: str = "*", object_class: Type[T] = None
    ) -> List[T]:
        # Simple glob-like matching for keys in the mock store
        matched_keys = [k for k in self._store.keys() if self._match_pattern(k, pattern)]
        return await self.get_many(matched_keys, object_class) if matched_keys else []
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        # A very basic glob pattern matcher. Does not handle complex globbing.
        # For simplicity, supporting only '*' at the end, or exact match.
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return key.startswith(pattern[:-1])
        return key == pattern


    async def update(self, key: str, data: Any) -> Error | None:
        return await self.create(key, data)

    async def batch_update(self, items: Dict[str, Any]) -> List[bool]:
        return await self.batch_create(items)

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def delete_many(self, keys: List[str]) -> int:
        deleted_count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                deleted_count += 1
        return deleted_count

    async def delete_all(self, pattern: str = "*") -> int:
        keys_to_delete = [k for k in self._store.keys() if self._match_pattern(k, pattern)]
        return await self.delete_many(keys_to_delete)
