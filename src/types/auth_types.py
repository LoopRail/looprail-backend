from enum import Enum

from pydantic import BaseModel


class Argon2HashConfig(BaseModel):
    time_cost: int
    memory_cost: int
    parallelism: int
    hash_len: int


class HashedPassword(BaseModel):
    password_hash: str


class WebhookProvider(str, Enum):
    BLOCKRADER = "blockrader"
