from pathlib import Path
from typing import Any

import yaml

from src.api.models import N8nNode, QueryType
from src.n8n_mapper.templates import postgres_node, mongodb_node, manual_trigger_node

_CREDS_PATH = Path(__file__).parent.parent.parent / "config" / "n8n_credentials.yaml"


def _load_credentials() -> dict[str, Any]:
    if _CREDS_PATH.exists():
        data = yaml.safe_load(_CREDS_PATH.read_text())
        return data.get("credentials", {})
    return {}


class N8nMapper:
    """Maps generated queries to n8n node definitions."""

    def __init__(self) -> None:
        self._creds = _load_credentials()

    def map_query(
        self,
        query_type: QueryType,
        query: str,
        parameters: list[Any],
        name: str = "Query Node",
        collection: str = "orders",
        position: list[int] | None = None,
    ) -> N8nNode:
        """Convert a query into an n8n node definition."""
        if query_type == QueryType.sql:
            cred = self._creds.get("postgres", {})
            raw = postgres_node(
                name=name,
                query=query,
                parameters=parameters,
                credential_id=str(cred.get("id", "1")),
                credential_name=cred.get("name", "PostgreSQL Dev"),
                position=position,
            )
        elif query_type == QueryType.mongodb:
            import json

            cred = self._creds.get("mongodb", {})
            try:
                pipeline = json.loads(query) if isinstance(query, str) else query
            except Exception:
                pipeline = []
            raw = mongodb_node(
                name=name,
                collection=collection,
                pipeline=pipeline,
                credential_id=str(cred.get("id", "2")),
                credential_name=cred.get("name", "MongoDB Dev"),
                position=position,
            )
        else:
            raise ValueError(f"Unsupported query type: {query_type}")

        return N8nNode(
            name=raw["name"],
            type=raw["type"],
            typeVersion=raw["typeVersion"],
            position=raw["position"],
            parameters=raw["parameters"],
            credentials=raw["credentials"],
        )

    def build_workflow(
        self,
        nodes: list[dict[str, Any]],
        name: str = "QueryMind Workflow",
    ) -> dict[str, Any]:
        """Wrap a list of nodes into a complete n8n workflow payload."""
        spacing = 250
        trigger = manual_trigger_node(position=[0, 300])
        all_nodes = [trigger] + [
            {**n, "position": [(i + 1) * spacing, 300]} for i, n in enumerate(nodes)
        ]

        connections: dict[str, Any] = {}
        for i in range(len(all_nodes) - 1):
            src = all_nodes[i]["name"]
            dst = all_nodes[i + 1]["name"]
            connections[src] = {"main": [[{"node": dst, "type": "main", "index": 0}]]}

        return {
            "name": name,
            "nodes": all_nodes,
            "connections": connections,
            "active": False,
            "settings": {},
        }
