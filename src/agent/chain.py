import json
from typing import Any

from src.agent.router import IntentRouter
from src.api.models import QueryResponse, QueryType, ValidationResult
from src.config import settings
from src.generators.mongo_gen import MongoGenerator
from src.generators.sql_gen import SQLGenerator
from src.memory.session import SessionManager
from src.memory.store import MemoryStore
from src.n8n_mapper.mapper import N8nMapper
from src.schema_loader.context_selector import ContextSelector


class QueryChain:
    """Orchestrates the full pipeline: route → schema → memory → generate → validate → map → store."""

    def __init__(self) -> None:
        self._router = IntentRouter()
        self._sql_gen = SQLGenerator()
        self._mongo_gen = MongoGenerator()
        self._mapper = N8nMapper()
        self._selector = ContextSelector()
        self._memory = MemoryStore()
        self._session = SessionManager()

    async def run(
        self,
        text: str,
        session_id: str,
        user_id: str,
        forced_type: QueryType | None = None,
        include_n8n_node: bool = True,
    ) -> QueryResponse:
        """Execute the full chain and return a QueryResponse."""
        state = await self._session.get(user_id, session_id)
        history: list[dict[str, str]] = state.get("history", [])

        query_type = forced_type or await self._router.route(text, history)

        if query_type == QueryType.unknown:
            return QueryResponse(
                query_type=QueryType.unknown,
                query="",
                validation=ValidationResult(
                    is_valid=False,
                    errors=["Intent unclear — please specify whether you want a SQL or MongoDB query."],
                ),
                session_id=session_id,
            )

        memories = await self._memory.search(text, user_id=user_id, query_type=query_type.value)
        await self._session.append_message(user_id, session_id, "user", text)

        if query_type == QueryType.sql:
            schema_ctx = await self._selector.select_postgres_context(text)
            query, parameters, validation = await self._sql_gen.generate(
                intent=text,
                schema_context=schema_ctx,
                memories=memories,
                history=history,
            )
            n8n_node = None
            if include_n8n_node and validation.is_valid:
                n8n_node = self._mapper.map_query(
                    query_type=QueryType.sql,
                    query=query,
                    parameters=parameters,
                    name=_name_from_intent(text),
                )
            tables_used = list(schema_ctx.get("tables", {}).keys())

        else:  # mongodb
            collection = _infer_collection(text)
            schema_ctx = await self._selector.select_mongo_context(text, collection)
            pipeline, validation = await self._mongo_gen.generate(
                intent=text,
                schema_context=schema_ctx,
                memories=memories,
                history=history,
            )
            query = json.dumps(pipeline)
            parameters = []
            n8n_node = None
            if include_n8n_node and validation.is_valid:
                n8n_node = self._mapper.map_query(
                    query_type=QueryType.mongodb,
                    query=query,
                    parameters=[],
                    name=_name_from_intent(text),
                    collection=collection,
                )
            tables_used = [collection]

        memory_stored = False
        if validation.is_valid:
            await self._memory.store(
                intent=text,
                query=query,
                query_type=query_type.value,
                tables_used=tables_used,
                user_id=user_id,
                success=True,
            )
            memory_stored = True
            await self._session.append_message(user_id, session_id, "assistant", query)

        return QueryResponse(
            query_type=query_type,
            query=query,
            parameters=parameters,
            validation=validation,
            n8n_node=n8n_node,
            memory_stored=memory_stored,
            session_id=session_id,
        )


def _name_from_intent(intent: str) -> str:
    words = intent.strip().split()[:6]
    return " ".join(w.capitalize() for w in words)


def _infer_collection(intent: str) -> str:
    lower = intent.lower()
    for coll in ("orders", "customers", "products", "order_items"):
        if coll.replace("_", " ") in lower or coll in lower:
            return coll
    return "orders"
