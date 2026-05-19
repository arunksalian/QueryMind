# QueryMind

An AI agent with memory that converts natural language into SQL/MongoDB queries and produces n8n workflow node definitions.

## Tech stack
- **Backend**: Python 3.12 + FastAPI (async everywhere)
- **LLM**: OpenAI GPT-4o / GPT-5 via `openai` SDK
- **Vector DB**: Qdrant (local Docker, port 6333) — long-term semantic memory
- **Cache**: Redis (port 6379) — session state + short-term chat history
- **SQL target**: PostgreSQL 16
- **NoSQL target**: MongoDB 7
- **Workflow engine**: n8n (self-hosted, REST API on port 5678)
- **Testing**: pytest + pytest-asyncio
- **Linting**: ruff + black

## Architecture

```
src/
├── agent/          # LLM orchestration — router, chain management
│   ├── router.py       # Intent detection: SQL vs MongoDB vs clarification
│   ├── chain.py        # Prompt chain assembly with schema context
│   └── prompts.py      # System/user prompt templates
├── generators/     # Query generation
│   ├── sql_gen.py      # Natural language → parameterized PostgreSQL
│   └── mongo_gen.py    # Natural language → aggregation pipelines
├── validators/     # Safety + syntax validation
│   ├── sql_validator.py    # sqlparse + dangerous pattern detection
│   └── mongo_validator.py  # Pipeline structure + operation whitelist
├── n8n_mapper/     # Query → n8n node JSON translation
│   ├── mapper.py       # Core mapping logic
│   └── templates.py    # n8n node type templates
├── schema_loader/  # DB introspection + semantic metadata
│   ├── introspector.py     # Auto-reads table/collection schemas
│   ├── context_selector.py # Vector similarity for relevant tables
│   └── annotations/        # YAML files with business context per table
├── memory/         # Agent memory system
│   ├── store.py        # Qdrant vector store for long-term memory
│   ├── session.py      # Redis session state manager
│   └── embedder.py     # OpenAI embeddings wrapper
├── api/            # FastAPI routes
│   ├── routes.py       # /query, /preview, /health endpoints
│   └── models.py       # Pydantic request/response schemas
```

## Coding standards
- Type hints on ALL functions — no untyped public APIs
- Pydantic models for all request/response schemas (use BaseModel)
- Async everywhere: `async def`, not sync — this includes DB calls
- Use `ruff` for linting, `black` for formatting (line length 88)
- Tests required for every generator and validator function
- Docstrings on all public functions (Google style)
- Environment variables via `pydantic-settings` (never hardcode secrets)

## Database conventions
- SQL: snake_case tables/columns, always use parameterized queries ($1, $2...)
- MongoDB: camelCase fields, aggregation pipelines preferred over find()
- NEVER generate DROP, TRUNCATE, or UPDATE/DELETE without WHERE
- Always include LIMIT on SELECT queries (default 100)

## n8n node output format
All generated nodes MUST follow this JSON structure:
```json
{
  "name": "NodeDisplayName",
  "type": "n8n-nodes-base.postgres",
  "parameters": {
    "operation": "executeQuery",
    "query": "SELECT ... FROM ... WHERE ... $1",
    "options": {}
  },
  "credentials": {
    "postgres": { "id": "CREDENTIAL_ID", "name": "CREDENTIAL_NAME" }
  }
}
```

## Key dependencies
- `openai` — LLM calls (GPT-4o/5)
- `fastapi` + `uvicorn` — HTTP server
- `qdrant-client` — vector memory store
- `redis` + `aioredis` — session cache
- `sqlparse` — SQL syntax validation
- `pymongo` — MongoDB query validation
- `pydantic` + `pydantic-settings` — data models + config
- `httpx` — async HTTP client for n8n API calls

## MCP servers available
- `postgres-dev`: local PostgreSQL — use for schema introspection and query validation
- `mongo-dev`: local MongoDB — use for collection sampling and pipeline testing
- `github`: repository management

## Common tasks
- "Generate a SQL query" → use /gen-sql skill
- "Generate a MongoDB query" → use /gen-mongo skill
- "Create an n8n node" → use /n8n-node skill
- "Add to memory" → use /add-memory skill
