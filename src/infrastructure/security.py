from dataclasses import dataclass

from src.infrastructure.constants import (
    ARGON2_HASH_LEN,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_SALT_LEN,
    ARGON2_TIME_COST,
)


@dataclass(init=False, frozen=True)
class Argon2Config:
    time_cost: int = ARGON2_TIME_COST
    memory_cost: int = ARGON2_MEMORY_COST
    parallelism: int = ARGON2_PARALLELISM
    hash_len: int = ARGON2_HASH_LEN
    salt_len: int = ARGON2_SALT_LEN
