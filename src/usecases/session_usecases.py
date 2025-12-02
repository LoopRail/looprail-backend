from src.models.session_model import SessionData
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
            user=user,
            device_id=device_id,
            ip_address=ip_address,
            device_type=device_type,
            expires_in_days=expires_in_days,
        )
        await self.redis_client.create(
            f"session:{session.session_id}",
            session.model_dump_json(),
            ttl=expires_in_days * 24 * 60 * 60,
        )
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
        return await self.redis_client.delete(f"session:{session_id}")
