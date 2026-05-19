from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.generators.sql_gen import SQLGenerator


@pytest.fixture
def mock_openai_response():
    """Return a mock OpenAI chat completion with a valid SELECT query."""
    msg = MagicMock()
    msg.content = (
        "SELECT o.id, o.total_amount / 100 AS revenue_usd\n"
        "FROM orders o\n"
        "WHERE o.status != $1\n"
        "LIMIT 100"
    )
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def schema_context():
    return {
        "tables": {
            "orders": {
                "columns": [
                    {"name": "id", "type": "uuid", "nullable": False, "default": None},
                    {"name": "total_amount", "type": "integer", "nullable": False, "default": None},
                    {"name": "status", "type": "text", "nullable": False, "default": None},
                ]
            }
        },
        "annotations": {
            "orders": {
                "description": "Customer purchase orders.",
                "business_context": "Divide total_amount by 100 for USD.",
            }
        },
    }


@pytest.mark.asyncio
async def test_generate_valid_query(mock_openai_response, schema_context):
    gen = SQLGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=mock_openai_response)):
        query, params, validation = await gen.generate("total revenue excluding cancelled orders", schema_context)

    assert "SELECT" in query
    assert validation.is_valid
    assert params == []


@pytest.mark.asyncio
async def test_generate_with_memories(mock_openai_response, schema_context):
    memories = [
        {"intent": "monthly revenue", "query": "SELECT SUM(total_amount) FROM orders LIMIT 100"}
    ]
    gen = SQLGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=mock_openai_response)):
        query, _, validation = await gen.generate("revenue this month", schema_context, memories=memories)

    assert validation.is_valid


@pytest.mark.asyncio
async def test_generate_returns_validation_warnings(schema_context):
    """A query without LIMIT produces a warning but is still valid (no errors)."""
    msg = MagicMock()
    msg.content = "SELECT id FROM orders WHERE status = $1"
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    gen = SQLGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=resp)):
        _, _, validation = await gen.generate("list order ids", schema_context)

    assert validation.is_valid
    assert any("LIMIT" in w for w in validation.warnings)


@pytest.mark.asyncio
async def test_generate_detects_dangerous_query(schema_context):
    msg = MagicMock()
    msg.content = "DROP TABLE orders"
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    gen = SQLGenerator()
    with patch.object(gen._client.chat.completions, "create", new=AsyncMock(return_value=resp)):
        _, _, validation = await gen.generate("drop everything", schema_context)

    assert not validation.is_valid
