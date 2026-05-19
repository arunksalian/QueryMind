from typing import Any


def postgres_node(
    name: str,
    query: str,
    parameters: list[Any],
    credential_id: str = "1",
    credential_name: str = "PostgreSQL Dev",
    position: list[int] | None = None,
) -> dict[str, Any]:
    """Build an n8n Postgres node definition."""
    return {
        "name": name,
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2,
        "position": position or [250, 300],
        "parameters": {
            "operation": "executeQuery",
            "query": query,
            "options": {
                "queryParams": _params_expression(parameters),
            },
        },
        "credentials": {
            "postgres": {"id": credential_id, "name": credential_name},
        },
    }


def mongodb_node(
    name: str,
    collection: str,
    pipeline: list[dict[str, Any]],
    credential_id: str = "2",
    credential_name: str = "MongoDB Dev",
    position: list[int] | None = None,
) -> dict[str, Any]:
    """Build an n8n MongoDB node definition."""
    import json

    return {
        "name": name,
        "type": "n8n-nodes-base.mongoDb",
        "typeVersion": 1,
        "position": position or [250, 300],
        "parameters": {
            "operation": "aggregate",
            "collection": collection,
            "query": json.dumps(pipeline),
            "options": {},
        },
        "credentials": {
            "mongoDb": {"id": credential_id, "name": credential_name},
        },
    }


def manual_trigger_node(position: list[int] | None = None) -> dict[str, Any]:
    """Build a manual trigger node to start a workflow."""
    return {
        "name": "Manual Trigger",
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": position or [0, 300],
        "parameters": {},
    }


def _params_expression(parameters: list[Any]) -> str:
    """Convert parameter list to n8n expression string."""
    if not parameters:
        return ""
    parts = [f"{{{{ $json.param{i + 1} }}}}" for i in range(len(parameters))]
    return ", ".join(parts)
