import hashlib
from typing import List, Optional, Tuple
from uuid import UUID

from src.infrastructure.logger import get_logger
from src.infrastructure.repositories import RefreshTokenRepository, SessionRepository
from src.infrastructure.security import Argon2Config
from src.models import RefreshToken, Session
from src.types import Error
from src.types.common_types import DeviceID, RefreshTokenId, SessionId, UserId
from src.utils.auth_utils import create_refresh_token, hash_password, verify_password

logger = get_logger(__name__)


class SessionUseCase:
    def __init__(
        self,
        refresh_token_expires_in_days: int,
        session_repository: SessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        argon2_config: Argon2Config,
    ):
        self.session_repository = session_repository
        self.refresh_token_repository = refresh_token_repository
        self.refresh_token_expires_in_days = refresh_token_expires_in_days
        self.argon2_config = argon2_config
        logger.debug(
            "SessionUseCase initialized with refresh token expiry: %s days",
            refresh_token_expires_in_days,
        )

    async def create_session(
        self,
        user_id: UserId,
        platform: str,
        device_id: DeviceID,
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

        # Enforce session limit (max 3 active sessions)
        active_sessions = await self.session_repository.get_active_sessions_ordered(
            user_id
        )
        if len(active_sessions) >= 3:
            oldest_session = active_sessions[0]
            logger.info(
                "User %s exceeded session limit (3). Revoking oldest session %s.",
                user_id,
                oldest_session.id,
            )
            err = await self.revoke_session(oldest_session.id)
            if err:
                logger.error(
                    "Failed to revoke oldest session %s for user %s: %s",
                    oldest_session.id,
                    user_id,
                    err.message,
                )
                # TODO look into this: We continue even if revocation fails, though ideally it shouldn't.

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
            new_refresh_token_string=refresh_token_string.clean(),
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
        return session, RefreshTokenId.new(refresh_token_string), None

    async def set_passcode(self, session_id: UUID, passcode: str) -> Error:
        """Set a 6-digit passcode for a specific session."""
        logger.info("Setting passcode for session %s", session_id)
        session, err = await self.get_session(session_id)
        if err or not session:
            return err

        hashed_passcode = hash_password(passcode, self.argon2_config)
        session.passcode_hash = hashed_passcode.password_hash

        _, err = await self.session_repository.update(session)
        if err:
            logger.error(
                "Failed to save passcode for session %s: %s", session_id, err.message
            )
            return err

        logger.info("Passcode set successfully for session %s", session_id)
        return None

    async def verify_passcode(
        self, session_id: SessionId, passcode: str
    ) -> Tuple[bool, Error]:
        """Verify a 6-digit passcode for a specific session."""
        logger.debug("Verifying passcode for session %s", session_id)
        session, err = await self.get_session(session_id)
        if err or not session:
            return False, err

        if not session.passcode_hash:
            logger.warning("Passcode not set for session %s", session_id)
            return False, None

        from src.types import HashedPassword

        is_valid = verify_password(
            passcode,
            HashedPassword(password_hash=session.passcode_hash),
            self.argon2_config,
        )
        return is_valid, None

    async def get_valid_refresh_token(
        self, session_id: SessionId
    ) -> Tuple[Optional[str], Error]:
        """Get the valid refresh token string for a specific session."""
        (
            refresh_token,
            err,
        ) = await self.refresh_token_repository.get_valid_refresh_token_for_session(
            session_id
        )
        if err or not refresh_token:
            return None, err
        # Note: The repository stores hashes. This is a problem if we need the raw token.
        # However, for rotation reuse, the client SHOULD already have the raw token.
        # If we want to return it on passcode login, we'd need to store it or return the hash (which is useless for the client).
        # Actually, if we reuse the token, the client already HAS the raw token from their previous session.
        # But if they cleared their cache, they might need it.
        # Usually, passcode login is for "fast login" on an EXISTING session.
        # I'll return the prefixed ID for now as a way to identify it.
        return refresh_token.get_prefixed_id(), None

    async def get_session(
        self, session_id: SessionId
    ) -> Tuple[Optional[Session], Error]:
        logger.debug("Getting session with ID: %s", session_id)
        session, err = await self.session_repository.get_session(session_id)
        print(session_id)
        print(session)
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
    ) -> Error:
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
            _,
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
        return None

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
