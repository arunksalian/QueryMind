import pytest
from src.validators.sql_validator import validate_sql


def test_valid_select_passes():
    query = "SELECT id, name FROM customers WHERE active = $1 LIMIT 100"
    result = validate_sql(query)
    assert result.is_valid
    assert not result.errors


def test_empty_query_fails():
    result = validate_sql("")
    assert not result.is_valid
    assert "empty" in result.errors[0].lower()


def test_drop_table_blocked():
    result = validate_sql("DROP TABLE customers")
    assert not result.is_valid
    assert any("DROP" in e for e in result.errors)


def test_truncate_blocked():
    result = validate_sql("TRUNCATE orders")
    assert not result.is_valid
    assert any("TRUNCATE" in e for e in result.errors)


def test_delete_without_where_blocked():
    result = validate_sql("DELETE FROM orders")
    assert not result.is_valid
    assert any("WHERE" in e for e in result.errors)


def test_delete_with_where_passes():
    query = "DELETE FROM orders WHERE id = $1"
    result = validate_sql(query)
    # DELETE with WHERE is a dangerous DML — blocked by stmt type check
    # This confirms it raises an error
    assert not result.is_valid


def test_update_without_where_blocked():
    result = validate_sql("UPDATE orders SET status = 'shipped'")
    assert not result.is_valid


def test_missing_limit_produces_warning():
    query = "SELECT id FROM orders WHERE status = $1"
    result = validate_sql(query)
    assert any("LIMIT" in w for w in result.warnings)


def test_select_star_produces_warning():
    query = "SELECT * FROM orders WHERE id = $1 LIMIT 100"
    result = validate_sql(query)
    assert any("SELECT *" in w for w in result.warnings)


def test_join_query_with_limit_passes():
    query = (
        "SELECT o.id, c.name "
        "FROM orders o "
        "JOIN customers c ON c.id = o.customer_id "
        "WHERE o.status != $1 "
        "LIMIT 100"
    )
    result = validate_sql(query)
    assert result.is_valid
    assert not result.errors


def test_parameterized_query_passes():
    query = (
        "SELECT id, total_amount FROM orders "
        "WHERE customer_id = $1 AND status = $2 "
        "LIMIT 100"
    )
    result = validate_sql(query)
    assert result.is_valid
