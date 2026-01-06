import hashlib
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from src.infrastructure import config
from src.infrastructure.repositories import RefreshTokenRepository, SessionRepository
from src.models import RefreshToken, Session
from src.types import Error


class SessionUseCase:
    def __init__(
        self,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository

    async def create_session(
        self,
        user_id: UUID,
        platform: str,
        device_id: str,
        ip_address: str,
        user_agent: str | None = None,
    ) -> Tuple[Optional[Session], str, Error]:
        session, err = await self.session_repository.create_session(
            user_id=user_id,
            platform=platform,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if err:
            return None, "", err

        refresh_token_string = str(uuid4())
        refresh_token, err = await self.refresh_token_repository.create_refresh_token(
            session_id=session.id,
            new_refresh_token_string=refresh_token_string,
            expires_in_days=config.jwt.refresh_token_expires_in_days,
        )
        if err:
            return None, "", err

        return session, refresh_token_string, None

    async def get_session(self, session_id: UUID) -> Tuple[Optional[Session], Error]:
        return await self.session_repository.get_session(session_id)

    async def revoke_session(self, session_id: UUID) -> Error:
        err = await self.session_repository.revoke_session(session_id)
        if err:
            return err
        err = await self.refresh_token_repository.revoke_refresh_tokens_for_session(
            session_id
        )
        if err:
            return err
        return None

    async def rotate_refresh_token(
        self, old_refresh_token: RefreshToken, new_refresh_token_string: str
    ) -> Tuple[Optional[RefreshToken], Error]:
        new_refresh_token_hash = hashlib.sha256(
            new_refresh_token_string.encode()
        ).hexdigest()
        err = await self.refresh_token_repository.mark_refresh_token_as_replaced(
            old_refresh_token=old_refresh_token,
            new_refresh_token_hash=new_refresh_token_hash,
        )
        if err:
            return None, err

        (
            new_refresh_token,
            err,
        ) = await self.refresh_token_repository.create_refresh_token(
            session_id=old_refresh_token.session_id,
            new_refresh_token_string=new_refresh_token_string,
            expires_in_days=config.jwt.refresh_token_expires_in_days,
        )
        if err:
            return None, err

        return new_refresh_token, None

    async def get_user_sessions(self, user_id: UUID) -> List[Session]:
        return await self.session_repository.get_user_sessions(user_id)

    async def revoke_all_user_sessions(self, user_id: UUID) -> Error:
        sessions = await self.session_repository.get_user_sessions(user_id)
        if not sessions:
            return None  # No sessions to revoke

        err = await self.session_repository.revoke_all_user_sessions(user_id)
        if err:
            return err

        for session in sessions:
            err = await self.refresh_token_repository.revoke_refresh_tokens_for_session(
                session.id
            )
            if err:
                return err  # or log and continue
        return None

    async def get_valid_refresh_token_by_hash(
        self, refresh_token_hash: str
    ) -> Tuple[Optional[RefreshToken], Error]:
        return await self.refresh_token_repository.get_valid_refresh_token_by_hash(
            refresh_token_hash
        )
