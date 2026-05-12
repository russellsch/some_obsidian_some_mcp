"""Helpers for building safe LanceDB WHERE clause filter expressions."""


def escape_filter_value(val: str) -> str:
    """Escape special characters in a value used in a LanceDB WHERE clause.

    LanceDB uses SQL-like filter expressions with double-quoted string literals.
    Escapes:
    - `"` — would break string literal boundaries
    - `%` and `_` — SQL LIKE wildcards that could match unintended patterns
    """
    val = val.replace('"', '\\"')
    val = val.replace("%", "\\%")
    val = val.replace("_", "\\_")
    return val
