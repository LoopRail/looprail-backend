from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models import Session
from src.types import Error, error


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

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

        err = await session.save(self.session)
        if err:
            return None, err
        return session, None

    async def get_session(self, session_id: UUID) -> Tuple[Optional[Session], Error]:
        statement = select(Session).where(
            Session.id == session_id, Session.revoked_at.is_(None)
        )
        result = await self.session.exec(statement)
        session = result.first()
        if not session:
            return None, error("Session not found or already revoked.")
        return session, None

    async def revoke_session(self, session_id: UUID) -> Error:
        session, err = await self.get_session(session_id)
        if err:
            return err

        session.revoked_at = datetime.utcnow()
        self.session.add(session)
        await self.session.commit()
        return None

    async def get_user_sessions(self, user_id: UUID) -> List[Session]:
        statement = select(Session).where(
            Session.user_id == user_id, Session.revoked_at.is_(None)
        )
        result = await self.session.exec(statement)
        return await result.all()

    async def revoke_all_user_sessions(self, user_id: UUID) -> Error:
        sessions = await self.get_user_sessions(user_id)
        for session in sessions:
            session.revoked_at = datetime.utcnow()
            self.session.add(session)
        await self.session.commit()
        return None
