---
name: gen-mongo
description: Generate a validated MongoDB aggregation pipeline from natural language input
---

# MongoDB query generation skill

When the user asks to generate a MongoDB query, follow these steps exactly:

## Step 1: Collection discovery
- Query the MongoDB MCP server (`mongo-dev`) to sample the target collection
- Run a sample of 10-20 documents to understand the field structure
- Check `src/schema_loader/annotations/` for YAML files with business context

## Step 2: Generate the pipeline
- Prefer aggregation pipelines over `find()` for anything beyond simple lookups
- Use camelCase field names consistently
- Include `$match` early in the pipeline to reduce documents processed
- Use `$project` to limit output fields
- Add `$limit` stage (default 100)
- For lookups across collections, use `$lookup` with pipeline syntax

## Step 3: Validate
- Pass the pipeline through `src/validators/mongo_validator.py`
- Ensure no dangerous operations ($out writing to existing collections, $merge without conditions)
- Verify all referenced fields exist in the sampled schema

## Step 4: Wrap for n8n
- Use the n8n MongoDB node template from `src/n8n_mapper/templates.py`
- Set operation to `aggregate`
- Pipeline goes in `query` as a JSON string

## Step 5: Test
- Add a test case in `tests/generators/test_mongo_gen.py`
- Test happy path, edge cases (missing fields, empty collections), and error cases

## Output format
Return both the raw pipeline and the n8n node JSON. Example:

```json
[
  { "$match": { "status": { "$ne": "cancelled" }, "createdAt": { "$gte": "ISODate('2024-01-01')" } } },
  { "$group": { "_id": "$customerId", "totalOrders": { "$sum": 1 }, "totalSpent": { "$sum": "$amount" } } },
  { "$sort": { "totalSpent": -1 } },
  { "$limit": 10 },
  { "$project": { "customerId": "$_id", "totalOrders": 1, "totalSpent": 1, "_id": 0 } }
]
```
