from openai import AsyncOpenAI

from src.config import settings


class Embedder:
    """Wraps OpenAI embeddings for vector memory storage and retrieval."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for a single text string."""
        response = await self._client.embeddings.create(input=text, model=self._model)
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a batch of texts."""
        response = await self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]
