import json
from typing import Any

from openai import AsyncOpenAI

from src.config import settings
from src.validators.mongo_validator import validate_mongo_pipeline
from src.api.models import ValidationResult

_SYSTEM_PROMPT = """\
You are a MongoDB expert. Generate a MongoDB aggregation pipeline as a JSON array.

Rules:
- Output ONLY a valid JSON array — no markdown, no explanation, no code fences
- Use camelCase field names
- Place $match early in the pipeline
- Always include $limit (default {limit})
- Use $project to limit output fields
- NEVER use $out to overwrite an existing collection
- NEVER use $merge without explicit whenMatched strategy

Collection schema (sampled fields):
{schema}

Business annotations:
{annotations}

Past similar pipelines for reference:
{memories}
"""


class MongoGenerator:
    """Generates MongoDB aggregation pipelines from natural language."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(
        self,
        intent: str,
        schema_context: dict[str, Any],
        memories: list[dict[str, Any]] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[list[dict[str, Any]], ValidationResult]:
        """Generate a MongoDB aggregation pipeline for the given intent.

        Returns (pipeline_list, validation_result).
        """
        schema_str = _format_schema(schema_context.get("schema", {}))
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
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": intent})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0,
            max_tokens=1024,
        )
        raw = (response.choices[0].message.content or "").strip()

        try:
            pipeline = json.loads(raw)
        except json.JSONDecodeError as exc:
            return [], ValidationResult(
                is_valid=False,
                errors=[f"LLM returned invalid JSON: {exc}"],
            )

        if not isinstance(pipeline, list):
            return [], ValidationResult(
                is_valid=False,
                errors=["Expected a JSON array, got a non-list value"],
            )

        validation = validate_mongo_pipeline(pipeline)
        return pipeline, validation


def _format_schema(schema: dict[str, Any]) -> str:
    fields = schema.get("fields", {})
    if not fields:
        return ""
    return "\n".join(f"  {k}: {', '.join(v)}" for k, v in fields.items())


def _format_annotations(annotations: dict[str, Any]) -> str:
    lines = []
    if annotations.get("description"):
        lines.append(f"  {annotations['description']}")
    if annotations.get("business_context"):
        lines.append(f"  Context: {annotations['business_context'].strip()}")
    return "\n".join(lines)


def _format_memories(memories: list[dict[str, Any]]) -> str:
    lines = []
    for m in memories:
        lines.append(f"  Intent: {m.get('intent', '')}")
        lines.append(f"  Pipeline: {m.get('query', '')}")
        lines.append("")
    return "\n".join(lines)
