from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    sql = "sql"
    mongodb = "mongodb"
    unknown = "unknown"


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language query")
    session_id: str = Field(..., description="Session identifier for memory continuity")
    user_id: str = Field("anonymous", description="User identifier")
    db_type: QueryType | None = Field(None, description="Force a specific DB type; auto-detected if omitted")
    include_n8n_node: bool = Field(True, description="Whether to include n8n node definition in response")


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class N8nNode(BaseModel):
    name: str
    type: str
    type_version: int = Field(alias="typeVersion", default=2)
    position: list[int] = Field(default_factory=lambda: [250, 300])
    parameters: dict[str, Any]
    credentials: dict[str, Any]

    model_config = {"populate_by_name": True}


class QueryResponse(BaseModel):
    query_type: QueryType
    query: str
    parameters: list[Any] = Field(default_factory=list, description="Bound parameter values ($1, $2...)")
    validation: ValidationResult
    n8n_node: N8nNode | None = None
    memory_stored: bool = False
    session_id: str


class PreviewRequest(BaseModel):
    query: str
    query_type: QueryType
    parameters: list[Any] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    services: dict[str, bool]
