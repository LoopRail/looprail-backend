import hashlib
from typing import List, Optional, Tuple

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import RefreshTokenRepository, SessionRepository
from src.models import RefreshToken, Session
from src.types import Error
from src.types.common_types import SessionId, UserId
from src.utils.auth_utils import create_refresh_token

logger = get_logger(__name__)


class SessionUseCase:
    def __init__(
        self,
        refresh_token_expires_in_days: int,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository
        self.refresh_token_expires_in_days = refresh_token_expires_in_days
        logger.debug(
            "SessionUseCase initialized with refresh token expiry: %s days",
            refresh_token_expires_in_days,
        )

    async def create_session(
        self,
        user_id: UserId,
        platform: str,
        device_id: str,
        ip_address: str,
        allow_notifications: bool = False,
        user_agent: str | None = None,
    ) -> Tuple[Optional[Session], str, Error]:
        logger.debug(
            "Creating session for user %s on platform %s, device %s from IP %s",
            user_id,
            platform,
            device_id,
            ip_address,
        )
        session, err = await self.session_repository.create_session(
            user_id=user_id,
            platform=platform,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            allow_notifications=allow_notifications,
        )
        if err:
            logger.error(
                "Failed to create session in repository for user %s: %s",
                user_id,
                err.message,
            )
            return None, "", err
        logger.debug("Session created in repository: %s", session.id)

        refresh_token_string = create_refresh_token()
        logger.debug("Creating refresh token for session %s", session.id)
        _, err = await self.refresh_token_repository.create_refresh_token(
            session_id=session.id,
            new_refresh_token_string=refresh_token_string,
            expires_in_days=self.refresh_token_expires_in_days,
        )
        if err:
            logger.error(
                "Failed to create refresh token for session %s: %s",
                session.id,
                err.message,
            )
            return None, "", err
        logger.info(
            "Session %s and refresh token created for user %s", session.id, user_id
        )
        return session, f"rft_{refresh_token_string}", None

    async def get_session(
        self, session_id: SessionId
    ) -> Tuple[Optional[Session], Error]:
        logger.debug("Getting session with ID: %s", session_id)
        session, err = await self.session_repository.get_session(session_id)
        if err:
            logger.debug("Session %s not found: %s", session_id, err.message)
            return None, err
        logger.debug("Session %s retrieved.", session_id)
        return session, err

    async def revoke_session(self, session_id: SessionId) -> Error:
        logger.info("Revoking session with ID: %s", session_id)
        err = await self.session_repository.revoke_session(session_id)
        if err:
            logger.error(
                "Failed to revoke session %s in repository: %s", session_id, err.message
            )
            return err
        logger.debug(
            "Session %s revoked in repository. Revoking associated refresh tokens.",
            session_id,
        )
        err = await self.refresh_token_repository.revoke_refresh_tokens_for_session(
            session_id
        )
        if err:
            logger.error(
                "Failed to revoke refresh tokens for session %s: %s",
                session_id,
                err.message,
            )
            return err
        logger.info("Session %s and associated refresh tokens revoked.", session_id)
        return None

    async def rotate_refresh_token(
        self, old_refresh_token: RefreshToken, new_refresh_token_string: str
    ) -> Tuple[Optional[RefreshToken], Error]:
        logger.debug(
            "Rotating refresh token for session %s", old_refresh_token.session_id
        )
        new_refresh_token_hash = hashlib.sha256(
            new_refresh_token_string.encode()
        ).hexdigest()
        err = await self.refresh_token_repository.mark_refresh_token_as_replaced(
            old_refresh_token=old_refresh_token,
            new_refresh_token_hash=new_refresh_token_hash,
        )
        if err:
            logger.error(
                "Failed to mark old refresh token %s as replaced: %s",
                old_refresh_token.id,
                err.message,
            )
            return None, err
        logger.debug("Old refresh token %s marked as replaced.", old_refresh_token.id)

        (
            new_refresh_token,
            err,
        ) = await self.refresh_token_repository.create_refresh_token(
            session_id=old_refresh_token.session_id,
            new_refresh_token_string=new_refresh_token_string,
            expires_in_days=self.refresh_token_expires_in_days,
        )
        if err:
            logger.error(
                "Failed to create new refresh token for session %s: %s",
                old_refresh_token.session_id,
                err.message,
            )
            return None, err
        logger.info(
            "Refresh token rotated successfully for session %s",
            old_refresh_token.session_id,
        )
        return new_refresh_token, None

    async def get_user_sessions(self, user_id: UserId) -> List[Session]:
        logger.debug("Getting all sessions for user %s", user_id)
        sessions = await self.session_repository.get_user_sessions(user_id)
        logger.debug("Retrieved %s sessions for user %s", len(sessions), user_id)
        return sessions

    async def revoke_all_user_sessions(self, user_id: UserId) -> Error:
        logger.info("Revoking all sessions for user %s", user_id)
        sessions = await self.session_repository.get_user_sessions(user_id)
        if not sessions:
            logger.info("No sessions to revoke for user %s", user_id)
            return None  # No sessions to revoke

        err = await self.session_repository.revoke_all_user_sessions(user_id)
        if err:
            logger.error(
                "Failed to revoke all sessions for user %s in repository: %s",
                user_id,
                err.message,
            )
            return err
        logger.debug(
            "All sessions for user %s revoked in repository. Revoking associated refresh tokens.",
            user_id,
        )

        for session in sessions:
            err = await self.refresh_token_repository.revoke_refresh_tokens_for_session(
                session.id
            )
            if err:
                logger.error(
                    "Failed to revoke refresh tokens for session %s (user %s): %s",
                    session.id,
                    user_id,
                    err.message,
                )
                return err  # or log and continue
        logger.info(
            "All sessions and associated refresh tokens revoked for user %s", user_id
        )
        return None

    async def get_valid_refresh_token_by_hash(
        self, refresh_token_hash: str
    ) -> Tuple[Optional[RefreshToken], Error]:
        logger.debug("Getting valid refresh token by hash.")
        (
            refresh_token,
            err,
        ) = await self.refresh_token_repository.get_valid_refresh_token_by_hash(
            refresh_token_hash
        )
        if err:
            logger.debug("Valid refresh token not found for hash: %s", err.message)
            return None, err
        logger.debug("Valid refresh token retrieved.")
        return refresh_token, err
