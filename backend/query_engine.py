"""Schema discovery, SQL safety validation, local read-only execution and chart shaping."""
import re
import sqlite3
from pathlib import Path
from typing import Any

from .database import DEFAULT_DB, get_connection

MAX_RESULT_ROWS = 500
SAFE_SQL_FUNCTIONS = {
    "abs", "avg", "coalesce", "concat", "concat_ws", "count", "date", "datetime",
    "dense_rank", "first_value", "format", "group_concat", "hex", "ifnull", "instr",
    "julianday", "lag", "last_value", "lead", "length", "like", "lower", "ltrim",
    "max", "min", "nullif", "nth_value", "ntile", "percent_rank", "printf", "rank",
    "replace", "round", "row_number", "rtrim", "sign", "sqlite_version", "strftime",
    "substr", "substring", "sum", "time", "total", "trim", "typeof", "unicode", "upper",
    "json", "json_array", "json_array_length", "json_extract", "json_insert", "json_object",
    "json_patch", "json_remove", "json_replace", "json_set", "json_type", "json_valid",
}
BLOCKED_WORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|ANALYZE|LOAD_EXTENSION)\b",
    re.IGNORECASE,
)


def discover_schema(db_path: str | Path = DEFAULT_DB) -> dict:
    conn = get_connection(db_path)
    try:
        objects = conn.execute("""SELECT name, type, sql FROM sqlite_master
            WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name""").fetchall()
        tables = []
        for obj in objects:
            name = obj["name"]
            columns = conn.execute(f'PRAGMA table_info("{name.replace(chr(34), chr(34)*2)}")').fetchall()
            foreign_keys = conn.execute(f'PRAGMA foreign_key_list("{name.replace(chr(34), chr(34)*2)}")').fetchall()
            tables.append({
                "name": name, "type": obj["type"],
                "columns": [{"name": c["name"], "type": c["type"], "nullable": not bool(c["notnull"]),
                             "primary_key": bool(c["pk"])} for c in columns],
                "foreign_keys": [{"column": fk["from"], "references_table": fk["table"],
                                  "references_column": fk["to"]} for fk in foreign_keys],
            })
        return {"tables": tables, "business_rules": {
            "sales_table": "sales_transactions",
            "valid_business_rows": "data_quality_issue IS NULL",
            "revenue_formula": "quantity * unit_price - discount_amount",
            "date_storage": "ISO-8601 YYYY-MM-DD text",
        }}
    finally:
        conn.close()


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql.strip()


def validate_and_execute(sql: str, parameters: list[Any] | None = None, db_path: str | Path = DEFAULT_DB) -> tuple[list[dict], list[str], str]:
    """Execute one SELECT in a read-only SQLite connection with an authorizer."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("The AI could not create a query for this question using the available data.")
    cleaned = _strip_sql_comments(sql)
    if len(cleaned) > 12000:
        raise ValueError("The generated query is too long.")
    if ";" in cleaned.rstrip(";"):
        raise ValueError("Only one SQL statement is allowed.")
    statement = cleaned.rstrip().rstrip(";").strip()
    if not re.match(r"^(SELECT|WITH)\b", statement, re.IGNORECASE):
        raise ValueError("Only read-only SELECT queries are allowed.")
    if BLOCKED_WORDS.search(statement):
        raise ValueError("The query contains a prohibited SQL operation.")

    db_path = Path(db_path).resolve()
    if not db_path.exists():
        raise RuntimeError("The local sales database has not been initialized.")
    uri = f"file:{db_path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        allowed_objects = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'")}

        def authorizer(action, arg1, arg2, database, trigger):
            if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ:
                return sqlite3.SQLITE_OK if arg1 in allowed_objects else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION:
                function_name = (arg2 or arg1 or "").lower()
                return sqlite3.SQLITE_OK if function_name in SAFE_SQL_FUNCTIONS else sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_DENY

        conn.set_authorizer(authorizer)
        conn.set_progress_handler(lambda: 1, 2_000_000)
        safe_parameters = parameters or []
        if not isinstance(safe_parameters, list) or len(safe_parameters) > 50:
            raise ValueError("The query contains an invalid parameter list.")
        if any(value is not None and not isinstance(value, (str, int, float, bool)) for value in safe_parameters):
            raise ValueError("The query contains an unsupported parameter value.")
        cursor = conn.execute(statement, safe_parameters)
        columns = [item[0] for item in cursor.description or []]
        rows = [dict(row) for row in cursor.fetchmany(MAX_RESULT_ROWS + 1)]
        truncated = len(rows) > MAX_RESULT_ROWS
        rows = rows[:MAX_RESULT_ROWS]
        if truncated:
            columns = columns
        return rows, columns, statement
    except sqlite3.DatabaseError as exc:
        message = str(exc)
        if "not authorized" in message.lower():
            raise ValueError("The generated query attempted an operation or table that is not permitted.") from exc
        if "interrupted" in message.lower():
            raise ValueError("The query exceeded the safe execution limit. Try narrowing the date range or filters.") from exc
        raise ValueError(f"SQLite could not execute the generated query: {message[:240]}") from exc
    finally:
        conn.close()


def chart_metadata(plan: dict, rows: list[dict], columns: list[str]) -> dict:
    numeric_columns = []
    if rows:
        for col in columns:
            if any(isinstance(row.get(col), (int, float)) and not isinstance(row.get(col), bool)
                   for row in rows if row.get(col) is not None):
                numeric_columns.append(col)
    x_key = plan.get("x_key") if plan.get("x_key") in columns else ""
    y_keys = [key for key in plan.get("y_keys", []) if key in numeric_columns]
    if not x_key:
        x_key = next((col for col in columns if col not in numeric_columns), "")
    if not y_keys:
        y_keys = numeric_columns[:3]
    chart_type = plan.get("chart_type", "table")
    if len(rows) <= 1 or not x_key or not y_keys:
        chart_type = "number" if len(rows) == 1 and numeric_columns else "table"
    if chart_type == "pie" and len(rows) > 12:
        chart_type = "bar"
    if chart_type not in {"bar", "line", "area", "pie", "table", "number"}:
        chart_type = "table"
    return {"type": chart_type, "title": plan.get("title") or "Query results",
            "x_key": x_key, "y_keys": y_keys}
