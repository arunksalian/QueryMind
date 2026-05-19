import uuid
from datetime import datetime, timezone
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue

from src.config import settings
from src.memory.embedder import Embedder

VECTOR_SIZE = 1536  # text-embedding-3-small output dimension


class MemoryStore:
    """Long-term semantic memory backed by Qdrant."""

    def __init__(self) -> None:
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection
        self._embedder = Embedder()

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist."""
        collections = await self._client.get_collections()
        names = [c.name for c in collections.collections]
        if self._collection not in names:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    async def store(
        self,
        intent: str,
        query: str,
        query_type: str,
        tables_used: list[str],
        user_id: str,
        success: bool = True,
    ) -> str:
        """Embed and store an intent-query pair. Returns the point ID."""
        vector = await self._embedder.embed(intent)
        point_id = str(uuid.uuid4())
        payload: dict[str, Any] = {
            "intent": intent,
            "query": query,
            "query_type": query_type,
            "tables_used": tables_used,
            "user_id": user_id,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._client.upsert(
            collection_name=self._collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
        return point_id

    async def search(
        self,
        intent: str,
        user_id: str,
        top_k: int = 3,
        query_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top-k semantically similar past interactions for a user."""
        vector = await self._embedder.embed(intent)

        must_conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        if query_type:
            must_conditions.append(FieldCondition(key="query_type", match=MatchValue(value=query_type)))

        results = await self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
            query_filter=Filter(must=must_conditions),
            with_payload=True,
        )
        return [{"score": r.score, **r.payload} for r in results if r.payload]
