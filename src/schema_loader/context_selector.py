from typing import Any

from src.memory.embedder import Embedder
from src.schema_loader.introspector import SchemaIntrospector


class ContextSelector:
    """Selects the most relevant tables/collections for a given user intent."""

    def __init__(self) -> None:
        self._introspector = SchemaIntrospector()
        self._embedder = Embedder()

    async def select_postgres_context(self, intent: str, top_k: int = 5) -> dict[str, Any]:
        """Return schema + annotations for the tables most relevant to the intent."""
        full_schema = await self._introspector.get_postgres_schema()
        annotations = self._introspector.load_annotations()

        if not full_schema:
            return {"tables": {}, "annotations": {}}

        # Build one description string per table for embedding comparison.
        table_names = list(full_schema.keys())
        table_descs = []
        for tbl in table_names:
            ann = annotations.get("tables", {}).get(tbl, {})
            desc = ann.get("description", tbl)
            cols = ", ".join(c["name"] for c in full_schema[tbl]["columns"])
            table_descs.append(f"{tbl}: {desc}. Columns: {cols}")

        intent_vec = await self._embedder.embed(intent)
        table_vecs = await self._embedder.embed_batch(table_descs)

        scores = [_cosine(intent_vec, tv) for tv in table_vecs]
        ranked = sorted(zip(scores, table_names), reverse=True)
        selected = [name for _, name in ranked[:top_k]]

        return {
            "tables": {t: full_schema[t] for t in selected if t in full_schema},
            "annotations": {t: annotations.get("tables", {}).get(t, {}) for t in selected},
        }

    async def select_mongo_context(self, intent: str, collection: str) -> dict[str, Any]:
        """Return sampled schema + annotations for a MongoDB collection."""
        schema = await self._introspector.get_mongo_schema(collection)
        annotations = self._introspector.load_annotations()
        return {
            "schema": schema,
            "annotations": annotations.get("collections", {}).get(collection, {}),
        }


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
