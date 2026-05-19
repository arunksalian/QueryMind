import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.generators.mongo_gen import MongoGenerator


@pytest.fixture
def valid_pipeline():
    return [
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": "$customerId", "totalSpent": {"$sum": "$totalAmount"}}},
        {"$sort": {"totalSpent": -1}},
        {"$limit": 10},
    ]


@pytest.fixture
def mock_response(valid_pipeline):
    msg = MagicMock()
    msg.content = json.dumps(valid_pipeline)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def schema_context():
    return {
        "schema": {
            "collection": "orders",
            "fields": {"customerId": ["str"], "totalAmount": ["int"], "status": ["str"]},
            "sample_count": 20,
        },
        "annotations": {
            "description": "MongoDB mirror of orders for analytics",
        },
    }


@pytest.mark.asyncio
async def test_generate_valid_pipeline(mock_response, schema_context, valid_pipeline):
    gen = MongoGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
        pipeline, validation = await gen.generate("top 10 customers by spending", schema_context)

    assert isinstance(pipeline, list)
    assert len(pipeline) == len(valid_pipeline)
    assert validation.is_valid


@pytest.mark.asyncio
async def test_generate_invalid_json_returns_error(schema_context):
    msg = MagicMock()
    msg.content = "not valid json {"
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    gen = MongoGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=resp)):
        pipeline, validation = await gen.generate("any intent", schema_context)

    assert pipeline == []
    assert not validation.is_valid
    assert any("JSON" in e for e in validation.errors)


@pytest.mark.asyncio
async def test_generate_non_list_json_returns_error(schema_context):
    msg = MagicMock()
    msg.content = json.dumps({"$match": {}})
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    gen = MongoGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=resp)):
        pipeline, validation = await gen.generate("any intent", schema_context)

    assert not validation.is_valid
    assert any("array" in e.lower() for e in validation.errors)


@pytest.mark.asyncio
async def test_generate_pipeline_missing_limit_warns(schema_context):
    pipeline_no_limit = [
        {"$match": {"status": "shipped"}},
        {"$project": {"customerId": 1}},
    ]
    msg = MagicMock()
    msg.content = json.dumps(pipeline_no_limit)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    gen = MongoGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=resp)):
        _, validation = await gen.generate("shipped orders", schema_context)

    assert validation.is_valid
    assert any("$limit" in w for w in validation.warnings)
