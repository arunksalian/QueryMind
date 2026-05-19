from openai import AsyncOpenAI

from src.api.models import QueryType
from src.agent.prompts import ROUTER_SYSTEM
from src.config import settings

_LABEL_MAP = {
    "sql": QueryType.sql,
    "mongodb": QueryType.mongodb,
    "clarify": QueryType.unknown,
}


class IntentRouter:
    """Classifies a user message as SQL, MongoDB, or unknown (needs clarification)."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def route(self, message: str, history: list[dict[str, str]] | None = None) -> QueryType:
        """Return the query type for a given message."""
        messages = [{"role": "system", "content": ROUTER_SYSTEM}]
        if history:
            messages.extend(history[-4:])
        messages.append({"role": "user", "content": message})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0,
            max_tokens=10,
        )
        label = (response.choices[0].message.content or "").strip().lower()
        return _LABEL_MAP.get(label, QueryType.unknown)
