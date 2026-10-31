from pathlib import Path
from .database import DEFAULT_DB, ensure_database, get_connection

# Only rows with completed status, valid date, positive quantity, valid non-negative
# unit price and non-negative discount are included in revenue.
VALID_WHERE = """
status = 'Completed'
AND data_quality_issue IS NULL
AND order_date IS NOT NULL
AND quantity > 0
AND unit_price IS NOT NULL
AND unit_price >= 0
AND discount_amount >= 0
AND (quantity * unit_price - discount_amount) >= 0
"""

def _run(sql: str, params=(), db_path: str | Path = DEFAULT_DB):
    ensure_database(db_path)
    conn = get_connection(db_path)
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

def _result(question, intent, answer, sql, rows, metrics=None):
    return {
        "question": question,
        "intent": intent,
        "answer": answer,
        "metrics": metrics or {},
        "supporting_data": rows,
        "sql": sql.strip(),
        "calculation_source": "SQLite query (deterministic)",
    }

def total_revenue(question="", db_path=DEFAULT_DB):
    sql = f"""SELECT ROUND(SUM(quantity * unit_price - discount_amount), 2) AS total_revenue,
                     COUNT(*) AS transaction_count
              FROM sales_transactions WHERE {VALID_WHERE}"""
    rows = _run(sql, db_path=db_path)
    amount = float(rows[0]["total_revenue"] or 0)
    count = int(rows[0]["transaction_count"] or 0)
    return _result(question, "total_revenue",
                   f"Total revenue is ₹{amount:,.2f} across {count} valid completed transactions.",
                   sql, rows, {"total_revenue": amount, "transaction_count": count})

def top_product(question="", db_path=DEFAULT_DB):
    sql = f"""SELECT product, ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue,
                     SUM(quantity) AS units_sold, COUNT(*) AS transaction_count
              FROM sales_transactions WHERE {VALID_WHERE}
              GROUP BY product ORDER BY revenue DESC, product ASC LIMIT 1"""
    rows = _run(sql, db_path=db_path)
    if not rows:
        return _result(question, "top_product", "No valid completed sales were found.", sql, [])
    r = rows[0]
    return _result(question, "top_product",
                   f"{r['product']} generated the highest revenue: ₹{r['revenue']:,.2f}.",
                   sql, rows, {"product": r["product"], "revenue": float(r["revenue"])})

def monthly_trend(question="", db_path=DEFAULT_DB):
    sql = f"""SELECT substr(order_date, 1, 7) AS month,
                     ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue,
                     COUNT(*) AS transaction_count
              FROM sales_transactions WHERE {VALID_WHERE}
              GROUP BY substr(order_date, 1, 7) ORDER BY month"""
    rows = _run(sql, db_path=db_path)
    return _result(question, "monthly_trend",
                   "Monthly revenue trend is calculated from valid completed transactions.",
                   sql, rows, {"months": len(rows)})

def top_region(question="", db_path=DEFAULT_DB):
    sql = f"""SELECT region, ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue,
                     SUM(quantity) AS units_sold, COUNT(*) AS transaction_count
              FROM sales_transactions WHERE {VALID_WHERE}
              GROUP BY region ORDER BY revenue DESC, region ASC LIMIT 1"""
    rows = _run(sql, db_path=db_path)
    if not rows:
        return _result(question, "top_region", "No valid completed sales were found.", sql, [])
    r = rows[0]
    return _result(question, "top_region",
                   f"{r['region']} generated the highest sales revenue: ₹{r['revenue']:,.2f}.",
                   sql, rows, {"region": r["region"], "revenue": float(r["revenue"])})

def month_comparison(month1: str, month2: str, question="", db_path=DEFAULT_DB):
    # Month values are normalized YYYY-MM and validated by the caller.
    sql = f"""SELECT substr(order_date, 1, 7) AS month,
                     ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue,
                     COUNT(*) AS transaction_count
              FROM sales_transactions
              WHERE {VALID_WHERE} AND substr(order_date, 1, 7) IN (?, ?)
              GROUP BY substr(order_date, 1, 7) ORDER BY month"""
    rows = _run(sql, (month1, month2), db_path)
    by_month = {r["month"]: float(r["revenue"] or 0) for r in rows}
    a, b = by_month.get(month1, 0.0), by_month.get(month2, 0.0)
    change = b - a
    pct = (change / a * 100) if a else None
    direction = "increased" if change > 0 else "decreased" if change < 0 else "did not change"
    if a == 0 and b != 0:
        change_text = f"Revenue {direction} from ₹0.00 to ₹{b:,.2f}; percentage change is undefined because the first month had zero revenue."
    else:
        pct_text = f"{abs(pct):.2f}%" if pct is not None else "undefined"
        change_text = f"Revenue {direction} by ₹{abs(change):,.2f} ({pct_text}) from {month1} to {month2}."
    answer = f"{month1}: ₹{a:,.2f}; {month2}: ₹{b:,.2f}. {change_text}"
    return _result(question, "month_comparison", answer, sql, rows,
                   {"month1": month1, "revenue1": a, "month2": month2,
                    "revenue2": b, "absolute_change": change, "percentage_change": pct})

def data_quality(db_path=DEFAULT_DB):
    sql = """SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN data_quality_issue IS NOT NULL THEN 1 ELSE 0 END) AS excluded_rows
        FROM sales_transactions"""
    rows = _run(sql, db_path=db_path)
    details_sql = """SELECT row_id, transaction_id, data_quality_issue
                     FROM sales_transactions
                     WHERE data_quality_issue IS NOT NULL
                     ORDER BY transaction_id"""
    details = _run(details_sql, db_path=db_path)
    return {"summary": rows[0], "excluded_records": details}


def dashboard_summary(db_path=DEFAULT_DB):
    """Return deterministic aggregates used by the React dashboard charts."""
    kpi_sql = f"""SELECT
        ROUND(COALESCE(SUM(quantity * unit_price - discount_amount), 0), 2) AS total_revenue,
        COUNT(*) AS transaction_count,
        ROUND(COALESCE(AVG(quantity * unit_price - discount_amount), 0), 2) AS average_transaction_value,
        COALESCE(SUM(quantity), 0) AS units_sold
        FROM sales_transactions WHERE {VALID_WHERE}"""
    monthly_sql = f"""SELECT substr(order_date, 1, 7) AS month,
        ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue,
        COUNT(*) AS transactions
        FROM sales_transactions WHERE {VALID_WHERE}
        GROUP BY substr(order_date, 1, 7) ORDER BY month"""
    region_sql = f"""SELECT region, ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue
        FROM sales_transactions WHERE {VALID_WHERE}
        GROUP BY region ORDER BY revenue DESC, region ASC"""
    product_sql = f"""SELECT product, ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue
        FROM sales_transactions WHERE {VALID_WHERE}
        GROUP BY product ORDER BY revenue DESC, product ASC LIMIT 6"""
    category_sql = f"""SELECT category, ROUND(SUM(quantity * unit_price - discount_amount), 2) AS revenue
        FROM sales_transactions WHERE {VALID_WHERE}
        GROUP BY category ORDER BY revenue DESC, category ASC"""
    return {
        "kpis": _run(kpi_sql, db_path=db_path)[0],
        "monthly_revenue": _run(monthly_sql, db_path=db_path),
        "revenue_by_region": _run(region_sql, db_path=db_path),
        "top_products": _run(product_sql, db_path=db_path),
        "revenue_by_category": _run(category_sql, db_path=db_path),
        "data_quality": data_quality(db_path),
    }
