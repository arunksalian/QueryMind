import re

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Keyword, DDL, DML

from src.api.models import ValidationResult

_DANGEROUS_PATTERNS = [
    (re.compile(r"\bDROP\s+(TABLE|DATABASE|INDEX|SCHEMA)\b", re.IGNORECASE), "DROP statements are forbidden"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE is forbidden"),
    (re.compile(r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)", re.IGNORECASE | re.DOTALL), "DELETE without WHERE is forbidden"),
    (re.compile(r"\bUPDATE\b(?!.*\bWHERE\b)", re.IGNORECASE | re.DOTALL), "UPDATE without WHERE is forbidden"),
    (re.compile(r";\s*--", re.IGNORECASE), "Suspicious comment after semicolon"),
    (re.compile(r"\bINTO\s+OUTFILE\b", re.IGNORECASE), "INTO OUTFILE is forbidden"),
]

_REQUIRED_PATTERNS = [
    (re.compile(r"\bLIMIT\b", re.IGNORECASE), "Query must include a LIMIT clause"),
]


def validate_sql(query: str) -> ValidationResult:
    """Check a SQL query for dangerous patterns and structural requirements."""
    errors: list[str] = []
    warnings: list[str] = []

    if not query.strip():
        return ValidationResult(is_valid=False, errors=["Query is empty"])

    # sqlparse parse check
    parsed = sqlparse.parse(query)
    if not parsed:
        return ValidationResult(is_valid=False, errors=["Could not parse SQL"])

    stmt: Statement = parsed[0]

    # Only allow SELECT statements
    stmt_type = stmt.get_type()
    if stmt_type and stmt_type.upper() not in ("SELECT", "UNKNOWN", None):
        if stmt_type.upper() in ("DROP", "CREATE", "ALTER", "TRUNCATE"):
            errors.append(f"DDL statement '{stmt_type}' is not allowed")
        elif stmt_type.upper() in ("INSERT", "UPDATE", "DELETE"):
            errors.append(f"DML write statement '{stmt_type}' requires explicit approval")

    flat = query.replace("\n", " ")

    for pattern, message in _DANGEROUS_PATTERNS:
        if pattern.search(flat):
            errors.append(message)

    for pattern, message in _REQUIRED_PATTERNS:
        if not pattern.search(flat):
            warnings.append(message)

    # Warn on SELECT *
    if re.search(r"SELECT\s+\*", flat, re.IGNORECASE):
        warnings.append("Avoid SELECT * — use explicit column names")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
