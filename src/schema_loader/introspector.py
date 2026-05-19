from pathlib import Path
from typing import Any

import asyncpg
import yaml
from motor.motor_asyncio import AsyncIOMotorClient

from src.config import settings

ANNOTATIONS_DIR = Path(__file__).parent / "annotations"


class SchemaIntrospector:
    """Reads table/collection schemas from live databases and YAML annotations."""

    async def get_postgres_schema(self, tables: list[str] | None = None) -> dict[str, Any]:
        """Return column definitions for the given tables (all public tables if None)."""
        conn = await asyncpg.connect(settings.postgres_dsn)
        try:
            where = ""
            args: list[Any] = []
            if tables:
                placeholders = ", ".join(f"${i + 1}" for i in range(len(tables)))
                where = f"AND table_name IN ({placeholders})"
                args = tables

            rows = await conn.fetch(
                f"""
                SELECT table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' {where}
                ORDER BY table_name, ordinal_position
                """,
                *args,
            )
        finally:
            await conn.close()

        schema: dict[str, Any] = {}
        for row in rows:
            tbl = row["table_name"]
            if tbl not in schema:
                schema[tbl] = {"columns": []}
            schema[tbl]["columns"].append(
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES",
                    "default": row["column_default"],
                }
            )
        return schema

    async def get_mongo_schema(self, collection: str, sample_size: int = 20) -> dict[str, Any]:
        """Infer schema by sampling documents from a MongoDB collection."""
        client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_uri)  # type: ignore[type-arg]
        db = client[settings.mongo_db]
        cursor = db[collection].find({}, limit=sample_size)
        docs = await cursor.to_list(length=sample_size)
        client.close()

        if not docs:
            return {"collection": collection, "fields": {}}

        field_types: dict[str, set[str]] = {}
        for doc in docs:
            for key, val in doc.items():
                field_types.setdefault(key, set()).add(type(val).__name__)

        return {
            "collection": collection,
            "fields": {k: list(v) for k, v in field_types.items()},
            "sample_count": len(docs),
        }

    def load_annotations(self) -> dict[str, Any]:
        """Load all YAML annotation files from the annotations directory."""
        merged: dict[str, Any] = {"tables": {}, "collections": {}}
        for path in ANNOTATIONS_DIR.glob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            if not data:
                continue
            for section in ("tables", "collections"):
                if section in data:
                    merged[section].update(data[section])
        return merged
