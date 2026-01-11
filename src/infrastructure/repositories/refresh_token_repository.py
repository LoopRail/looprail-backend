import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlmodel import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models import RefreshToken
from src.types import Error, error
from src.types.common_types import SessionId, UserId


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

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
        err = refresh_token.save(self.session)
        if err:
            return None, err
        return refresh_token, None

    async def get_valid_refresh_token_by_hash(
        self, refresh_token_hash: str
    ) -> Tuple[Optional[RefreshToken], Error]:
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == refresh_token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
            RefreshToken.replaced_by_hash.is_(None),
        )
        result = await self.session.exec(statement)
        refresh_token = result.first()
        if not refresh_token:
            return None, error("Invalid or expired refresh token")
        return refresh_token, None

    async def mark_refresh_token_as_replaced(
        self, old_refresh_token: RefreshToken, new_refresh_token_hash: str
    ) -> Error:
        old_refresh_token.replaced_by_hash = new_refresh_token_hash
        self.session.add(old_refresh_token)
        await self.session.commit()
        return None

    async def revoke_refresh_tokens_for_session(self, session_id: SessionId) -> Error:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.session_id == session_id)
            .values(revoked_at=datetime.utcnow())
        )
        await self.session.exec(statement)
        await self.session.commit()
        return None

    async def revoke_all_refresh_tokens_for_user(self, user_id: UserId) -> Error:
        # This requires joining with the Session table to find all sessions for a user
        # and then revoking their refresh tokens.
        # This will be handled in SessionRepository or SessionUseCase
        return error(
            "Not implemented: revoke_all_refresh_tokens_for_user in RefreshTokenRepository"
        )
