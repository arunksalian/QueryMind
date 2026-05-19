---
name: gen-sql
description: Generate a validated, parameterized PostgreSQL query from natural language input
---

# SQL query generation skill

When the user asks to generate a SQL query, follow these steps exactly:

## Step 1: Schema discovery
- Query the PostgreSQL MCP server (`postgres-dev`) to get schemas for relevant tables
- Run: `SELECT table_name, column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema = 'public'`
- Check `src/schema_loader/annotations/` for YAML files with business context

## Step 2: Generate the query
- Use parameterized format: `$1, $2, $3...` (never string interpolation)
- Always include a LIMIT clause (default 100)
- Use explicit column names (never `SELECT *` in production queries)
- Prefer JOINs over subqueries where possible
- Add comments explaining complex logic

## Step 3: Validate
- Pass the query through `src/validators/sql_validator.py`
- Ensure no dangerous operations (DROP, TRUNCATE, DELETE without WHERE)
- Run EXPLAIN against the dev database via MCP to check the query plan

## Step 4: Wrap for n8n
- Use the n8n Postgres node template from `src/n8n_mapper/templates.py`
- Set `operation: "executeQuery"`
- Include parameter bindings in `options.queryParams`

## Step 5: Test
- Add a test case in `tests/generators/test_sql_gen.py`
- Test happy path, edge cases (NULLs, empty results), and error cases

## Output format
Return both the raw SQL and the n8n node JSON. Example:

```sql
-- Monthly revenue by product category
SELECT c.name AS category, SUM(oi.quantity * oi.unit_price) / 100 AS revenue_usd
FROM order_items oi
JOIN products p ON p.id = oi.product_id
JOIN categories c ON c.id = p.category_id
JOIN orders o ON o.id = oi.order_id
WHERE o.status != 'cancelled'
  AND o.created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')
  AND o.created_at < DATE_TRUNC('month', NOW())
GROUP BY c.name
ORDER BY revenue_usd DESC
LIMIT 100;
```
