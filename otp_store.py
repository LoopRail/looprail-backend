#src/storage/otp_store.py

from src.infrastructure.redis import RedisClient
from src.infrastructure.settings import settings
from src.models.otp_model import Otp
from src.types import error, Error

# Initialize async Redis client using your RedisConfig from settings
redis_client = RedisClient(settings.redis)

def _otp_key(email: str, otp_type: str) -> str:
    """Generate Redis key for OTP storage."""
    return f"otp:{otp_type}:{email}"

async def save_otp(otp: Otp) -> Error | None:
    """
    Save an OTP instance to Redis with automatic expiration.
    """
    key = _otp_key(otp.user_email, otp.otp_type.value)
    ttl = otp.expires_at - otp.created_at
    return await redis_client.create(key, otp, ttl=ttl)

async def get_otp(email: str, otp_type: str = "email_verification") -> tuple[Otp | None, Error | None]:
    """
    Retrieve an OTP from Redis.
    """
    key = _otp_key(email, otp_type)
    return await redis_client.get(key, Otp)

async def delete_otp(email: str, otp_type: str = "email_verification") -> bool:
    """
    Delete an OTP record from Redis.
    """
    key = _otp_key(email, otp_type)
    return await redis_client.delete(key)
