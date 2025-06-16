import json
from datetime import timedelta
from typing import Generic, TypeVar, Optional
from uuid import UUID

from fastapi_sessions.backends.session_backend import (
    SessionBackend,
    SessionModel,
)
from pydantic import ValidationError
from redis.asyncio import Redis

from core.config import SESSION_EXPIRE_MINUTES

ID = TypeVar("ID")
Data = TypeVar("Data", bound=SessionModel)


class RedisBackend(SessionBackend[ID, Data], Generic[ID, Data]):
    def __init__(self, redis: Redis, session_model: type[Data]):
        """
        Initializes a Redis-backed session backend.
        Args:
            redis (Redis): An asyncio-compatible Redis client instance.
            session_model (type[Data]): The Pydantic model for session data.
        """
        self._redis = redis
        self._session_model = session_model
        self._expire = timedelta(minutes=SESSION_EXPIRE_MINUTES)

    async def create(self, session_id: ID, data: Data) -> None:
        await self._redis.set(
            f"session:{session_id}",
            data.model_dump_json(),
            ex=self._expire,
        )

    async def read(self, session_id: ID) -> Optional[Data]:
        raw_data = await self._redis.get(f"session:{session_id}")
        if not raw_data:
            return None

        try:
            return self._session_model.model_validate_json(raw_data)
        except (ValidationError, json.JSONDecodeError):
            # If data is corrupted or not valid, treat it as missing
            return None

    async def update(self, session_id: ID, data: Data) -> None:
        await self.create(session_id, data)  # SET with EX is atomic

    async def delete(self, session_id: ID) -> None:
        await self._redis.delete(f"session:{session_id}") 