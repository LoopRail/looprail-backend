from datetime import datetime
from typing import List, Optional, Tuple

from src.infrastructure.repositories.base import Base
from src.models import Session
from src.types import Error
from src.types.common_types import DeviceID, SessionId, UserId


class SessionRepository(Base[Session]):
    _model = Session

    async def create_session(
        self,
        user_id: UserId,
        platform: str,
        device_id: DeviceID,
        ip_address: str,
        allow_notifications: bool = False,
        user_agent: str | None = None,
    ) -> Tuple[Optional[Session], Error]:
        session_instance = (
            Session(  # Renamed variable to avoid conflict with method name
                user_id=user_id,
                platform=platform,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent,
                allow_notifications=allow_notifications,
            )
        )

        return await self.create(session_instance)

    async def get_session(
        self, session_id: SessionId
    ) -> Tuple[Optional[Session], Error]:
        return await self.find_one(id=session_id, revoked_at=None)

    async def revoke_session(self, session_id: SessionId) -> Error:
        session, err = await self.get_session(session_id)
        if err:
            return err
        session.revoked_at = datetime.utcnow()
        _, err = await self.update(session)
        return err

    async def get_user_sessions(self, user_id: UserId) -> List[Session]:
        return await self.find_all(user_id=user_id, revoked_at=None)

    async def get_active_sessions_ordered(self, user_id: UserId) -> List[Session]:
        """Get active sessions for a user, ordered by last_seen_at ascending (oldest first)."""
        # Note: find_all doesn't support ordering yet, we might need a custom query if find_all is too limited.
        # However, for 3-4 sessions, sorting in memory is fine if repository doesn't support it directly.
        sessions = await self.get_user_sessions(user_id)
        return sorted(sessions, key=lambda s: s.last_seen_at)

    async def revoke_all_user_sessions(self, user_id: UserId) -> Error:
        sessions = await self.get_user_sessions(user_id)
        for session_instance in sessions:
            session_instance.revoked_at = datetime.utcnow()
            _, err = await self.update(session_instance)
            if err:
                return err
        return None
