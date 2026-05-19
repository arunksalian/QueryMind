# QueryMind 🧠

An AI agent with memory that converts natural language into SQL/MongoDB queries and produces n8n workflow node definitions.

## Quick start

### 1. Start infrastructure
```bash
docker compose up -d
```

### 2. Install Python dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your OpenAI API key and other settings
```

### 4. Run the API server
```bash
uvicorn src.api.routes:app --reload --host 0.0.0.0 --port 8000
```

## Development with Claude Code

This project is optimized for Claude Code with:
- **CLAUDE.md** — full project context loaded every session
- **MCP servers** — live Postgres + MongoDB access for schema introspection
- **Hooks** — auto-lint, auto-format, auto-test on every file write
- **Skills** — `/gen-sql`, `/gen-mongo`, `/n8n-node`, `/add-memory`
- **Subagents** — `sql-writer`, `mongo-writer`, `test-writer`

### Setup MCP servers
```bash
claude mcp add --scope project --transport stdio postgres-dev \
  -- npx @modelcontextprotocol/server-postgres postgresql://localhost:5432/querymind_dev

claude mcp add --scope project --transport stdio mongo-dev \
  -- npx @modelcontextprotocol/server-mongodb mongodb://localhost:27017/querymind_dev
```

### Example Claude Code session
```
> Build the SQL generator that handles JOIN queries across orders, customers, and products
> Generate a MongoDB pipeline for top 10 customers by spending
> Wrap both as n8n nodes and connect them in a workflow
```

## Architecture

```
User (natural language) → FastAPI → Agent Router → SQL/Mongo Generator → Validator → n8n Mapper → n8n API
                                        ↕
                               Memory Store (Qdrant + Redis)
```

## License

MIT
