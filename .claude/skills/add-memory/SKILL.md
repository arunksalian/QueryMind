---
name: add-memory
description: Store and retrieve query patterns, user preferences, and conversation context in the agent's memory system
---

# Memory management skill

When working with QueryMind's memory system:

## Storing a new memory
After generating a successful query, store the intent-query pair:
1. Extract the user's natural language intent
2. Pair it with the generated query (SQL or MongoDB)
3. Embed using `src/memory/embedder.py` (OpenAI text-embedding-3-small)
4. Store in Qdrant via `src/memory/store.py` with metadata:
   - `intent`: original natural language
   - `query_type`: "sql" or "mongodb"
   - `query`: the generated query string
   - `tables_used`: list of tables/collections referenced
   - `timestamp`: ISO 8601
   - `user_id`: session user identifier
   - `success`: whether the query executed successfully

## Retrieving memories
When a user references past context ("like last time", "the report query", "same as before"):
1. Embed the current request
2. Search Qdrant for top-3 similar past interactions
3. Include matched memories in the LLM prompt as few-shot examples
4. Prefer recent memories over older ones (time-decay scoring)

## Session memory (short-term)
- Store in Redis with key pattern: `session:{user_id}:{thread_id}`
- TTL: 24 hours
- Contains: last 20 messages, current schema context, active DB type
- Use `src/memory/session.py` for all session operations

## When to use this skill
- After every successful query generation → store the pair
- When user references past interactions → retrieve and inject context
- When building the prompt context → merge session + long-term memories
