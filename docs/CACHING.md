# Caching Architecture & Usage Guide

This document outlines the caching strategy implemented in the LoopRail backend to optimize performance and reduce database load.

## Overview

LoopRail uses **Redis** as a distributed caching layer. The primary goal is to cache frequently accessed, relatively static data like user profiles, while ensuring that real-time financial data (balances, assets) remains dynamic and consistent.

## Cache Service

The `CacheService` acts as a standardized wrapper around Redis operations.

- **Source:** `src/infrastructure/services/cache_service.py`
- **Pattern:** Cache-Aside (Lazy Loading)

### Core Methods

| Method                      | Description                                                                    |
| :-------------------------- | :----------------------------------------------------------------------------- |
| `get(prefix, id, model)`    | Retrieves an object from cache. Optionally validates against a Pydantic model. |
| `set(prefix, id, obj, ttl)` | Stores an object (dict or Pydantic model) in cache with a TTL.                 |
| `delete(prefix, id)`        | Removes a specific entry from the cache.                                       |
| `invalidate_prefix(prefix)` | Clears all keys belonging to a specific namespace (e.g., `user:*`).            |

---

## Caching Strategy by Entity

### 1. User Profiles (`user:*`)

User profiles are cached to accelerate authentication and account detail retrieval.

- **Cache Hit:** When fetching by ID, the system checks Redis first.
- **Cache Miss:** Data is fetched from the database and then populated into Redis.
- **Invalidation:** The cache is automatically deleted whenever a user or their profile is updated.

**Relevant Use Cases:** `UserUseCase.get_user_by_id`, `UserUseCase.update_user`, `UserUseCase.save`.

### 2. Wallet Assets & Balances

To ensure absolute financial accuracy, **wallet balances and asset lists are NOT cached**. Every request for a balance or asset list triggers a fresh retrieval from the database and the Blnk Ledger.

---

## Developer Usage

### Injection

Inject the `CacheService` into your use cases via the dependency injection layer.

```python
class MyUseCase:
    def __init__(self, cache: CacheService):
        self.cache = cache
```

### Example: Get & Set

```python
# Try cache
data = await self.cache.get("example", "123", MyModel)
if not data:
    # SQL Fetch
    data = await self.repo.get_by_id("123")
    # Set cache (TTL defaults to 1 hour)
    await self.cache.set("example", "123", data)
```

### Example: Delete (Invalidation)

```python
await self.repo.update_item("123", **params)
await self.cache.delete("example", "123")
```

---

## Key Prefixes

| Prefix    | Usage                   | Current TTL    |
| :-------- | :---------------------- | :------------- |
| `user`    | User model data         | 1 Hour (3600s) |
| `session` | User session validation | Session-based  |
