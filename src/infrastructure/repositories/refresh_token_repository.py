import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlmodel import select, update

from src.infrastructure.repositories.base import Base
from src.models import RefreshToken
from src.types import Error, error
from src.types.common_types import SessionId


class RefreshTokenRepository(Base[RefreshToken]):
    _model = RefreshToken

    async def create_refresh_token(
        self,
        session_id: SessionId,
        new_refresh_token_string: str,
        expires_in_days: int = 30,
    ) -> Tuple[Optional[RefreshToken], Error]:
        refresh_token_hash = hashlib.sha256(
            new_refresh_token_string.encode()
        ).hexdigest()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        refresh_token = RefreshToken(
            session_id=session_id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
        )
        return await self.create(refresh_token)

    async def get_valid_refresh_token_by_hash(
        self, refresh_token_hash: str
    ) -> Tuple[Optional[RefreshToken], Error]:
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == refresh_token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
            # RefreshToken.replaced_by_hash.is_(None),
        )
        result = await self.session.execute(statement)
        refresh_token = result.scalars().first()
        print(refresh_token)
        if not refresh_token:
            return None, error("Invalid or expired refresh token")
        return refresh_token, None

    async def get_valid_refresh_token_for_session(
        self, session_id: SessionId
    ) -> Tuple[Optional[RefreshToken], Error]:
        statement = select(RefreshToken).where(
            RefreshToken.session_id == session_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
            RefreshToken.replaced_by_hash.is_(None),
        )
        result = await self.session.execute(statement)
        refresh_token = result.scalars().first()
        if not refresh_token:
            return None, error("No valid refresh token found for session")
        return refresh_token, None

    async def mark_refresh_token_as_replaced(
        self, old_refresh_token: RefreshToken, new_refresh_token_hash: str
    ) -> Error:
        old_refresh_token.replaced_by_hash = new_refresh_token_hash
        self.session.add(old_refresh_token)
        return None

    async def revoke_refresh_tokens_for_session(self, session_id: SessionId) -> Error:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.session_id == session_id)
            .values(revoked_at=datetime.utcnow())
        )
        await self.session.execute(statement)
        return None
