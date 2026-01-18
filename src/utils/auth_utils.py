import hashlib
import base64
from uuid import uuid4
import hmac
import re
from typing import Optional

from argon2 import PasswordHasher, exceptions

from src.infrastructure.security import Argon2Config
from src.types.auth_types import HashedPassword
from src.types.common_types import RefreshTokenId
from src.types.error import Error, error


def get_password_hasher(config: Argon2Config) -> PasswordHasher:
    return PasswordHasher(
        time_cost=config.time_cost,
        memory_cost=config.memory_cost,
        parallelism=config.parallelism,
        hash_len=config.hash_len,
    )


def hash_password(password: str, config: Argon2Config) -> HashedPassword:
    """
    Hash a password or PIN using Argon2 with your Argon2Config.
    Returns a HashedPassword object containing the encoded hash string.
    """
    ph = get_password_hasher(config)
    hashed = ph.hash(password)
    return HashedPassword(password_hash=hashed)


def verify_password(
    password: str, hashed_obj: HashedPassword, config: Argon2Config
) -> bool:
    """
    Verify a password or PIN against an Argon2 encoded hash.
    """
    ph = get_password_hasher(config)
    try:
        return ph.verify(hashed_obj.password_hash, password)
    except exceptions.VerifyMismatchError:
        return False


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
    if not 8 <= len(password) <= 64:
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


def verify_signature(
    body: bytes,
    received_signature: str,
    secret: str,
) -> bool:
    """
    Verify webhook signature using HMAC-SHA512.
    """
    computed_signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(computed_signature, received_signature)


def create_refresh_token() -> RefreshTokenId:
    """
    Generates a random string for a refresh token.
    """
    refresh_token = RefreshTokenId.new(str(uuid4()))
    return refresh_token


def compute_pkce_challenge(code_verifier: str) -> str:
    """
    Compute S256 code challenge from code verifier.
    """
    code_verifier_clean = code_verifier.strip()
    hashed = hashlib.sha256(code_verifier_clean.encode("ascii")).digest()
    return base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")

