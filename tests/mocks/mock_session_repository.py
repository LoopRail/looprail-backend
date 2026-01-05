from typing import List, Optional, Tuple
from uuid import UUID

from src.models import Session
from src.types import Error, error


class MockSessionRepository:
    def __init__(self, db_session):
        self.db_session = db_session
        self.sessions = [] # For mocking storage

    async def create_session(
        self,
        user_id: UUID,
        platform: str,
        device_id: str,
        ip_address: str,
        user_agent: str | None = None,
    ) -> Tuple[Optional[Session], Error]:
        session = Session(
            user_id=user_id,
            platform=platform,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        # Simulate saving to DB
        self.sessions.append(session)
        self.db_session.add(session)
        self.db_session.commit()
        self.db_session.refresh(session)
        return session, None

    async def get_session(self, session_id: UUID) -> Tuple[Optional[Session], Error]:
        for s in self.sessions:
            if s.id == session_id and s.revoked_at is None:
                return s, None
        return None, error("Session not found or already revoked.")

    async def revoke_session(self, session_id: UUID) -> Error:
        for s in self.sessions:
            if s.id == session_id:
                s.revoked_at = datetime.utcnow()
                # Simulate DB update
                return None
        return error("Session not found.")

    async def get_user_sessions(self, user_id: UUID) -> List[Session]:
        return [s for s in self.sessions if s.user_id == user_id and s.revoked_at is None]

    async def revoke_all_user_sessions(self, user_id: UUID) -> Error:
        for s in self.sessions:
            if s.user_id == user_id:
                s.revoked_at = datetime.utcnow()
        # Simulate DB update
        return None
