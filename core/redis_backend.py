import redis.asyncio as redis
from uuid import UUID
from typing import Optional, Type
from pydantic import BaseModel
from fastapi_sessions.backends.session_backend import SessionBackend, SessionModel

class RedisBackend(SessionBackend[UUID, SessionModel]):
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def create(self, session_id: UUID, data: SessionModel) -> None:
        await self.redis.set(str(session_id), data.model_dump_json())

    async def read(self, session_id: UUID, model: Type[SessionModel]) -> Optional[SessionModel]:
        raw_data = await self.redis.get(str(session_id))
        if not raw_data:
            return None
        return model.model_validate_json(raw_data)

    async def update(self, session_id: UUID, data: SessionModel) -> None:
        await self.redis.set(str(session_id), data.model_dump_json())

    async def delete(self, session_id: UUID) -> None:
        await self.redis.delete(str(session_id))
