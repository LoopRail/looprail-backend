import base64
import hashlib
import secrets
from typing import Optional, Tuple

from pydantic import BaseModel

from src.infrastructure.logger import get_logger
from src.infrastructure.redis import RedisClient
from src.types import ChallengeId, Error, error
from src.utils.auth_utils import compute_pkce_challenge

logger = get_logger(__name__)


class AuthChallenge(BaseModel):
    challenge_id: ChallengeId
    code_challenge: str
    nonce: str


class SecurityUseCase:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.challenge_prefix = "auth_challenge:"
        self.challenge_ttl = 300  # 5 minutes

    async def create_challenge(
        self, code_challenge: str
    ) -> Tuple[Optional[AuthChallenge], Error]:
        """Create a new PKCE challenge and nonce, stored in Redis."""
        challenge_id = ChallengeId.new(secrets.token_hex(16))
        nonce = secrets.token_hex(16)
        code_challenge = compute_pkce_challenge(code_challenge)

        challenge = AuthChallenge(
            challenge_id=challenge_id, code_challenge=code_challenge, nonce=nonce
        )

        err = await self.redis_client.create(
            key=f"{self.challenge_prefix}{challenge_id}",
            data=challenge,
            ttl=self.challenge_ttl,
        )
        if err:
            logger.error("Failed to store challenge in Redis: %s", err.message)
            return None, err

        logger.info("Created auth challenge: %s", challenge_id)
        return challenge, None

    async def verify_pkce(
        self, challenge_id: str, code_verifier: str
    ) -> Tuple[bool, Error]:
        """
        Verify the code_verifier against the stored code_challenge (S256).
        """
        key = f"{self.challenge_prefix}{challenge_id}"
        challenge_data, err = await self.redis_client.get(key, AuthChallenge)
        if err or not challenge_data:
            logger.warning("Challenge not found or expired: %s", challenge_id)
            return False, error("Challenge expired or invalid")

        encoded = compute_pkce_challenge(code_verifier)

        if encoded != challenge_data.code_challenge:
            logger.warning("PKCE verification failed for challenge %s", challenge_id)
            return False, None

        await self.redis_client.delete([key])

        logger.info("PKCE verification successful for challenge %s", challenge_id)
        return True, None
