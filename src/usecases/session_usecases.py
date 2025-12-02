from typing import List
from src.models.session_model import SessionData, UserSession
from src.infrastructure.redis import RedisClient
from src.dtos.user_dtos import UserPublic
from uuid import UUID


class SessionUseCase:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client

    async def create_session(
        self,
        user: UserPublic,
        device_id: str,
        ip_address: str,
        device_type: str | None = None,
        expires_in_days: int = 30,
    ) -> SessionData:
        session = SessionData.new_session(
            user_id=user.id,
            device_id=device_id,
            ip_address=ip_address,
            device_type=device_type,
            expires_in_days=expires_in_days,
        )

        user_session, _ = await self.redis_client.get(
            f"user_sessions:{user.id}", UserSession
        )
        if not user_session:
            user_session = UserSession(user_id=user.id, user_public_data=user)
        else:
            user_session.user_public_data = user # Update user public data if it exists

        user_session.session_ids.append(session.session_id)

        tx = await self.redis_client.transaction()
        await tx.create(
            f"session:{session.session_id}",
            session.model_dump_json(),
            ttl=expires_in_days * 24 * 60 * 60,
        )
        await tx.create(
            f"user_sessions:{user.id}",
            user_session.model_dump_json(),
        )
        await tx.commit()

        return session

    async def get_session(self, session_id: UUID) -> SessionData | None:
        session_data, err = await self.redis_client.get(
            f"session:{session_id}", SessionData
        )
        if err:
            return None
        if session_data and session_data.is_expired():
            await self.delete_session(session_id)
            return None
        return session_data

    async def delete_session(self, session_id: UUID) -> bool:
        session_data, _ = await self.get_session(session_id)
        if not session_data:
            return False

        user_session, _ = await self.redis_client.get(
            f"user_sessions:{session_data.user_id}", UserSession
        )

        if user_session:
            if session_id in user_session.session_ids:
                user_session.session_ids.remove(session_id)
                await self.redis_client.create(
                    f"user_sessions:{session_data.user_id}",
                    user_session.model_dump_json(),
                )

        return await self.redis_client.delete(f"session:{session_id}")

    async def get_user_sessions(self, user_id: UUID) -> List[SessionData]:
        user_session, _ = await self.redis_client.get(
            f"user_sessions:{user_id}", UserSession
        )
        if not user_session:
            return []

        session_keys = [f"session:{sid}" for sid in user_session.session_ids]
        sessions = await self.redis_client.get_many(session_keys, SessionData)

        valid_sessions = [s for s in sessions if s]

        if len(valid_sessions) != len(sessions):
            valid_session_ids = {s.session_id for s in valid_sessions}
            user_session.session_ids = [
                sid for sid in user_session.session_ids if sid in valid_session_ids
            ]
            await self.redis_client.create(
                f"user_sessions:{user_id}",
                user_session.model_dump_json(),
            )

        return valid_sessions
