---
name: n8n-node
description: Transform a validated query into an n8n workflow node definition
---

# n8n node mapping skill

When creating an n8n node definition from a generated query:

## Step 1: Identify the node type
Map the query type to the correct n8n node:
- PostgreSQL → `n8n-nodes-base.postgres`
- MySQL → `n8n-nodes-base.mySql`
- MongoDB → `n8n-nodes-base.mongoDb`

## Step 2: Build the node JSON
Use the template from `src/n8n_mapper/templates.py`. Required fields:
- `name`: Human-readable description of what the query does
- `type`: The n8n node identifier
- `typeVersion`: Use latest (1.0 for most DB nodes)
- `position`: [x, y] coordinates in the workflow canvas
- `parameters`: Query-specific config
- `credentials`: Reference to stored n8n credentials

## Step 3: Handle parameters by DB type

### PostgreSQL node
```json
{
  "operation": "executeQuery",
  "query": "SELECT ... WHERE id = $1",
  "options": {
    "queryParams": "={{ $json.userId }}"
  }
}
```

### MongoDB node
```json
{
  "operation": "aggregate",
  "collection": "orders",
  "query": "[{\"$match\": ...}]",
  "options": {}
}
```

## Step 4: Validate against n8n API
- Load credentials config from `config/n8n_credentials.yaml`
- If n8n is running locally, POST to `http://localhost:5678/api/v1/workflows` to validate

## Step 5: Support workflow chaining
When the user wants multiple queries connected:
- Generate each node with sequential positions
- Add connection definitions between nodes
- Include a trigger node (Manual Trigger or Webhook) as the entry point

## Output
Always return the complete node JSON that can be directly POSTed to n8n's REST API.
