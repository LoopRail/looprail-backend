import re
import secrets
from typing import Optional

from argon2.low_level import Type, hash_secret_raw

from src.infrastructure.settings import Argon2Config
from src.types.auth_types import HashedPassword
from src.types.error import Error, error


def hash_password_argon2(password: str, argon2_config: Argon2Config) -> HashedPassword:
    """Hash password using Argon2 with custom configuration"""

    pwd_bytes = password.encode("utf-8")

    salt = secrets.token_bytes(argon2_config.salt_len)

    hash_bytes = hash_secret_raw(
        secret=pwd_bytes,
        salt=salt,
        time_cost=argon2_config.time_cost,
        memory_cost=argon2_config.memory_cost,
        parallelism=argon2_config.parallelism,
        hash_len=argon2_config.hash_len,
        type=Type.ID,
    )

    return HashedPassword(
        password_hash=hash_bytes.hex(),
        salt=salt.hex(),
    )


def verify_password_argon2(
    password: str, hashed_password_obj: HashedPassword, argon2_config: Argon2Config
) -> bool:
    """Verify password against stored Argon2 hash"""

    pwd_bytes = password.encode("utf-8")
    salt_bytes = bytes.fromhex(hashed_password_obj.salt)

    new_hash = hash_secret_raw(
        secret=pwd_bytes,
        salt=salt_bytes,
        time_cost=argon2_config.time_cost,
        memory_cost=argon2_config.memory_cost,
        parallelism=argon2_config.parallelism,
        hash_len=argon2_config.hash_len,
        type=Type.ID,
    )

    return new_hash.hex() == hashed_password_obj.hash


def validate_password_strength(password: str) -> Optional[Error]:
    """
    Validates the strength of a password based on the following rules:
    - Minimum 8 characters.
    - Maximum 64 characters.
    - At least one uppercase letter.
    - At least one lowercase letter.
    - At least one digit.
    - At least one special character from the set [@, #, $, %, ^, &, +, = or !].
    """
    if 8 <= len(password) <= 64:
        return error("Password must be between 8 and 64 characters long.")
    if not re.search(r"[a-z]", password):
        return error("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        return error("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        return error("Password must contain at least one digit.")
    if not re.search(r"[@#$%^&+=!]", password):
        return error(
            "Password must contain at least one special character (@, #, $, %, ^, &, +, = or !)."
        )
    return None
