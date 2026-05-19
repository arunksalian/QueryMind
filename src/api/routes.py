import asyncpg
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from qdrant_client import AsyncQdrantClient

from src.agent.chain import QueryChain
from src.api.models import (
    HealthResponse,
    PreviewRequest,
    PreviewResponse,
    QueryRequest,
    QueryResponse,
    QueryType,
)
from src.config import settings

app = FastAPI(title="QueryMind", version="0.1.0")

_chain: QueryChain | None = None


def _get_chain() -> QueryChain:
    global _chain
    if _chain is None:
        _chain = QueryChain()
    return _chain


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Convert natural language to a SQL or MongoDB query."""
    chain = _get_chain()
    result = await chain.run(
        text=request.text,
        session_id=request.session_id,
        user_id=request.user_id,
        forced_type=request.db_type,
        include_n8n_node=request.include_n8n_node,
    )
    if not result.validation.is_valid:
        raise HTTPException(status_code=422, detail={
            "errors": result.validation.errors,
            "query_type": result.query_type,
        })
    return result


@app.post("/preview", response_model=PreviewResponse)
async def preview(request: PreviewRequest) -> PreviewResponse:
    """Execute a generated query against the dev database and return sample rows."""
    if request.query_type == QueryType.sql:
        try:
            conn = await asyncpg.connect(settings.postgres_dsn)
            try:
                rows = await conn.fetch(request.query, *request.parameters)
                data = [dict(r) for r in rows[:100]]
                return PreviewResponse(
                    rows=data,
                    row_count=len(data),
                    truncated=len(data) == 100,
                )
            finally:
                await conn.close()
        except Exception as exc:
            return PreviewResponse(error=str(exc))

    elif request.query_type == QueryType.mongodb:
        import json

        try:
            pipeline = json.loads(request.query)
            client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_uri)  # type: ignore[type-arg]
            db = client[settings.mongo_db]
            collection_name = "orders"
            cursor = db[collection_name].aggregate(pipeline)
            docs = await cursor.to_list(length=100)
            client.close()
            for doc in docs:
                doc.pop("_id", None)
            return PreviewResponse(
                rows=docs,
                row_count=len(docs),
                truncated=len(docs) == 100,
            )
        except Exception as exc:
            return PreviewResponse(error=str(exc))

    raise HTTPException(status_code=400, detail="Unsupported query type for preview")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Check connectivity to all backing services."""
    checks: dict[str, bool] = {}

    try:
        conn = await asyncpg.connect(settings.postgres_dsn)
        await conn.fetchval("SELECT 1")
        await conn.close()
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False

    try:
        client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_uri)  # type: ignore[type-arg]
        await client.admin.command("ping")
        client.close()
        checks["mongodb"] = True
    except Exception:
        checks["mongodb"] = False

    try:
        r = await aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    try:
        qc = AsyncQdrantClient(url=settings.qdrant_url)
        await qc.get_collections()
        checks["qdrant"] = True
    except Exception:
        checks["qdrant"] = False

    overall = "ok" if all(checks.values()) else "degraded"
    return HealthResponse(status=overall, services=checks)
