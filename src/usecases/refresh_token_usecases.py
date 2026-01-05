import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from src.models import RefreshTokenData
from src.infrastructure.config import settings

class RefreshTokenUseCase:
    def __init__(self):
        # This will later take a repository as a dependency
        pass

    async def create_refresh_token(
        self,
        session_id: UUID,
        expires_in_days: int = settings.REFRESH_TOKEN_EXP_DAYS,
    ) -> tuple[str, RefreshTokenData]:
        raw_token = self._generate_random_token()
        token_hash = self._hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        refresh_token_data = RefreshTokenData(
            session_id=session_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        # In a real implementation, this would save to a database via a repository
        # For now, we return the raw token and the data object
        return raw_token, refresh_token_data

    async def validate_and_rotate_refresh_token(
        self, refresh_token: str
    ) -> tuple[Optional[RefreshTokenData], Optional[str]]:
        # This is a placeholder. Real implementation will involve DB lookup and updates.
        # 1. Hash the incoming refresh_token
        # 2. Look up in DB for a matching token_hash that is not expired and not revoked
        # 3. If found:
        #    a. Check for reuse (if replaced_by_hash is not None and matches current token_hash)
        #    b. Revoke the old refresh token (set revoked_at)
        #    c. Generate a new raw_token and new_token_hash
        #    d. Update the old token's replaced_by_hash to the new_token_hash
        #    e. Create and save a new RefreshTokenData with the new_token_hash
        #    f. Return the new raw_token and the session associated with the original token
        # 4. If not found or invalid, return None, None
        return None, None

    async def revoke_refresh_token(self, token_hash: str) -> None:
        # Placeholder for revoking a token
        pass

    async def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        # Placeholder for revoking all tokens for a user
        pass

    def _generate_random_token(self) -> str:
        return os.urandom(32).hex()

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

