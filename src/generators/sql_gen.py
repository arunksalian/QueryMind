from typing import Any

from openai import AsyncOpenAI

from src.config import settings
from src.validators.sql_validator import validate_sql
from src.api.models import ValidationResult

_SYSTEM_PROMPT = """\
You are a PostgreSQL expert. Generate a single, parameterized PostgreSQL SELECT query.

Rules:
- Use $1, $2, $3... for all user-supplied values (never string interpolation)
- Always include LIMIT (default {limit})
- Use explicit column names (never SELECT *)
- Prefer JOINs over subqueries
- NEVER generate DROP, TRUNCATE, DELETE without WHERE, or UPDATE without WHERE
- Output ONLY valid SQL — no markdown, no explanation

Schema context:
{schema}

Business annotations:
{annotations}

Past similar queries for reference:
{memories}
"""


class SQLGenerator:
    """Generates parameterized PostgreSQL queries from natural language."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(
        self,
        intent: str,
        schema_context: dict[str, Any],
        memories: list[dict[str, Any]] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, list[Any], ValidationResult]:
        """Generate a SQL query for the given intent.

        Returns (query, parameters, validation_result).
        Parameters list is empty — values come from the caller at runtime.
        """
        schema_str = _format_schema(schema_context.get("tables", {}))
        ann_str = _format_annotations(schema_context.get("annotations", {}))
        mem_str = _format_memories(memories or [])

        system = _SYSTEM_PROMPT.format(
            limit=settings.query_default_limit,
            schema=schema_str or "No schema available.",
            annotations=ann_str or "No annotations available.",
            memories=mem_str or "None.",
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        if history:
            messages.extend(history[-6:])  # last 3 turns
        messages.append({"role": "user", "content": intent})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0,
            max_tokens=1024,
        )
        query = (response.choices[0].message.content or "").strip()
        validation = validate_sql(query)
        return query, [], validation


def _format_schema(tables: dict[str, Any]) -> str:
    lines = []
    for tbl, info in tables.items():
        cols = ", ".join(
            f"{c['name']} {c['type']}{'?' if c['nullable'] else ''}"
            for c in info.get("columns", [])
        )
        lines.append(f"  {tbl}({cols})")
    return "\n".join(lines)


def _format_annotations(annotations: dict[str, Any]) -> str:
    lines = []
    for tbl, ann in annotations.items():
        if ann.get("description"):
            lines.append(f"  {tbl}: {ann['description']}")
        if ann.get("business_context"):
            lines.append(f"    Context: {ann['business_context'].strip()}")
    return "\n".join(lines)


def _format_memories(memories: list[dict[str, Any]]) -> str:
    lines = []
    for m in memories:
        lines.append(f"  Intent: {m.get('intent', '')}")
        lines.append(f"  Query:  {m.get('query', '')}")
        lines.append("")
    return "\n".join(lines)
