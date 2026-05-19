import json
from typing import Any

import redis.asyncio as aioredis

from src.config import settings

MAX_HISTORY = 20


class SessionManager:
    """Short-term chat history and context stored in Redis."""

    def __init__(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._ttl = settings.session_ttl_seconds

    def _key(self, user_id: str, session_id: str) -> str:
        return f"session:{user_id}:{session_id}"

    async def get(self, user_id: str, session_id: str) -> dict[str, Any]:
        """Load session state; returns empty state if session does not exist."""
        raw = await self._redis.get(self._key(user_id, session_id))
        if raw is None:
            return {"history": [], "schema_context": None, "db_type": None}
        return json.loads(raw)

    async def append_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Append a message to session history, capping at MAX_HISTORY entries."""
        state = await self.get(user_id, session_id)
        state["history"].append({"role": role, "content": content})
        state["history"] = state["history"][-MAX_HISTORY:]
        await self._save(user_id, session_id, state)

    async def set_context(
        self,
        user_id: str,
        session_id: str,
        schema_context: str | None = None,
        db_type: str | None = None,
    ) -> None:
        """Update schema context and db_type in session state."""
        state = await self.get(user_id, session_id)
        if schema_context is not None:
            state["schema_context"] = schema_context
        if db_type is not None:
            state["db_type"] = db_type
        await self._save(user_id, session_id, state)

    async def clear(self, user_id: str, session_id: str) -> None:
        await self._redis.delete(self._key(user_id, session_id))

    async def _save(self, user_id: str, session_id: str, state: dict[str, Any]) -> None:
        await self._redis.setex(
            self._key(user_id, session_id),
            self._ttl,
            json.dumps(state),
        )
