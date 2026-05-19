from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.models import QueryResponse, QueryType, ValidationResult
from src.api.routes import app

client = TestClient(app)


def _valid_response(**kwargs) -> QueryResponse:
    defaults = dict(
        query_type=QueryType.sql,
        query="SELECT id FROM orders WHERE status = $1 LIMIT 100",
        parameters=["active"],
        validation=ValidationResult(is_valid=True),
        n8n_node=None,
        memory_stored=True,
        session_id="sess-1",
    )
    defaults.update(kwargs)
    return QueryResponse(**defaults)


@pytest.mark.asyncio
async def test_query_endpoint_success():
    with patch("src.api.routes._get_chain") as mock_get_chain:
        chain = MagicMock()
        chain.run = AsyncMock(return_value=_valid_response())
        mock_get_chain.return_value = chain

        resp = client.post("/query", json={
            "text": "show me active orders",
            "session_id": "sess-1",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["query_type"] == "sql"
    assert "SELECT" in data["query"]


@pytest.mark.asyncio
async def test_query_endpoint_validation_error():
    with patch("src.api.routes._get_chain") as mock_get_chain:
        chain = MagicMock()
        chain.run = AsyncMock(return_value=_valid_response(
            validation=ValidationResult(is_valid=False, errors=["DROP is forbidden"]),
            query="DROP TABLE orders",
        ))
        mock_get_chain.return_value = chain

        resp = client.post("/query", json={
            "text": "drop all orders",
            "session_id": "sess-1",
        })

    assert resp.status_code == 422


def test_health_endpoint_returns_200():
    with (
        patch("src.api.routes.asyncpg.connect", new=AsyncMock()) as mock_pg,
        patch("src.api.routes.AsyncIOMotorClient") as mock_mongo,
        patch("src.api.routes.aioredis.from_url") as mock_redis,
        patch("src.api.routes.AsyncQdrantClient") as mock_qdrant,
    ):
        # Configure all mocks to look healthy
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=1)
        conn.close = AsyncMock()
        mock_pg.return_value = conn

        mongo_client = MagicMock()
        mongo_client.admin.command = AsyncMock(return_value={"ok": 1})
        mongo_client.close = MagicMock()
        mock_mongo.return_value = mongo_client

        redis_client = AsyncMock()
        redis_client.ping = AsyncMock()
        redis_client.aclose = AsyncMock()
        mock_redis.return_value = redis_client

        qdrant_client = AsyncMock()
        qdrant_client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
        mock_qdrant.return_value = qdrant_client

        resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data
