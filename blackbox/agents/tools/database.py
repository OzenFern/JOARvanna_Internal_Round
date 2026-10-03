"""blackbox/agents/tools/database.py — In-memory database tool for text2sql tasks."""
from __future__ import annotations
import re
from typing import Any

# ── Demo schema ────────────────────────────────────────────────────────────────
SCHEMA = {
    "orders": {
        "columns": ["order_id", "customer_id", "amount", "region", "status", "created_at"],
        "rows": [
            (1, 101, 250.0,  "north", "completed", "2024-01-10"),
            (2, 102, 480.0,  "south", "completed", "2024-01-12"),
            (3, 103, 125.5,  "north", "pending",   "2024-01-14"),
            (4, 101, 390.0,  "east",  "completed", "2024-01-15"),
            (5, 104, 720.0,  "west",  "cancelled", "2024-01-16"),
            (6, 102,  95.0,  "south", "completed", "2024-01-18"),
            (7, 105, 310.0,  "north", "completed", "2024-01-20"),
            (8, 103, 540.0,  "east",  "pending",   "2024-01-21"),
        ],
    },
    "customers": {
        "columns": ["customer_id", "name", "tier", "city"],
        "rows": [
            (101, "Alice",   "gold",   "Boston"),
            (102, "Bob",     "silver", "Austin"),
            (103, "Carol",   "bronze", "Denver"),
            (104, "David",   "gold",   "Chicago"),
            (105, "Eve",     "silver", "Seattle"),
        ],
    },
}

def get_schema() -> dict[str, list[str]]:
    """Return table → column list mapping."""
    return {table: info["columns"] for table, info in SCHEMA.items()}

def execute_sql(sql: str) -> list[dict[str, Any]]:
    """
    Extremely limited SQL executor: handles SELECT … FROM … WHERE … and aggregates.
    Raises ValueError for unsupported queries.
    """
    sql = sql.strip().rstrip(";")
    sql_upper = sql.upper()

    # Identify table
    m = re.search(r"FROM\s+(\w+)", sql_upper)
    if not m:
        raise ValueError("No FROM clause found")
    table_name = m.group(1).lower()
    if table_name not in SCHEMA:
        raise ValueError(f"Unknown table: {table_name!r}")

    table  = SCHEMA[table_name]
    cols   = table["columns"]
    rows   = [dict(zip(cols, row)) for row in table["rows"]]

    # WHERE filter (simple key=value or key>'value')
    where_m = re.search(r"WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|$)", sql, re.IGNORECASE | re.DOTALL)
    if where_m:
        cond = where_m.group(1).strip()
        rows = _apply_where(rows, cond)

    # SELECT columns / aggregates
    sel_m = re.match(r"SELECT\s+(.+?)\s+FROM", sql, re.IGNORECASE | re.DOTALL)
    if not sel_m:
        raise ValueError("No SELECT clause")
    select_expr = sel_m.group(1).strip()

    # COUNT(*)
    if re.match(r"COUNT\(\*\)", select_expr, re.IGNORECASE):
        return [{"count": len(rows)}]

    # SUM(col)
    sum_m = re.match(r"SUM\((\w+)\)", select_expr, re.IGNORECASE)
    if sum_m:
        col = sum_m.group(1).lower()
        return [{"sum": sum(float(r[col]) for r in rows if col in r)}]

    # AVG(col)
    avg_m = re.match(r"AVG\((\w+)\)", select_expr, re.IGNORECASE)
    if avg_m:
        col = avg_m.group(1).lower()
        vals = [float(r[col]) for r in rows if col in r]
        return [{"avg": sum(vals) / len(vals) if vals else 0}]

    # Column list
    if select_expr == "*":
        return rows
    selected_cols = [c.strip().lower() for c in select_expr.split(",")]
    return [{c: r.get(c) for c in selected_cols} for r in rows]


def _apply_where(rows: list[dict], cond: str) -> list[dict]:
    """Parse a single WHERE condition (no AND/OR) and filter rows."""
    for pattern, op_fn in [
        (r"(\w+)\s*=\s*'?([^']+)'?",  lambda a, b: str(a).lower() == str(b).lower()),
        (r"(\w+)\s*>\s*([0-9.]+)",     lambda a, b: float(a) > float(b)),
        (r"(\w+)\s*<\s*([0-9.]+)",     lambda a, b: float(a) < float(b)),
        (r"(\w+)\s*>=\s*([0-9.]+)",    lambda a, b: float(a) >= float(b)),
    ]:
        m = re.match(pattern, cond.strip())
        if m:
            col, val = m.group(1).lower(), m.group(2)
            return [r for r in rows if op_fn(r.get(col, ""), val)]
    return rows
