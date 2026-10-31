import csv
import math
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "sales.db"
DEFAULT_CSV = ROOT / "data" / "sales_data.csv"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_transactions (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT,
    order_date TEXT,
    product TEXT,
    category TEXT,
    region TEXT,
    sales_channel TEXT,
    quantity INTEGER,
    unit_price REAL,
    discount_amount REAL,
    status TEXT,
    data_quality_issue TEXT
);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_transactions(order_date);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_transactions(product);
CREATE INDEX IF NOT EXISTS idx_sales_region ON sales_transactions(region);
"""

def get_connection(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def _number(value: Any, field: str):
    """Parse numeric CSV values without silently truncating fractional quantities."""
    if value is None or str(value).strip() == "":
        return None
    try:
        number = float(value)
        if not math.isfinite(number):
            return None
        if field == "quantity":
            if not number.is_integer():
                return None
            return int(number)
        return number
    except (TypeError, ValueError, OverflowError):
        return None

def import_csv(csv_path: str | Path = DEFAULT_CSV, db_path: str | Path = DEFAULT_DB) -> dict:
    """Load source rows without deleting bad data; mark rows excluded from revenue."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        # Re-import is repeatable: replace rows with the supplied source snapshot.
        conn.execute("DELETE FROM sales_transactions")
        inserted = 0
        seen_transaction_ids = set()
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {
                "Transaction_Id", "Order_date", "Product", "Category", "Region",
                "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
            }
            if not required.issubset(set(reader.fieldnames or [])):
                missing = sorted(required - set(reader.fieldnames or []))
                raise ValueError(f"CSV is missing required columns: {missing}")

            for row in reader:
                issues = []
                try:
                    order_date = datetime.strptime(row["Order_date"].strip(), "%d-%m-%Y").date().isoformat()
                except (ValueError, AttributeError):
                    order_date = None
                    issues.append("invalid order date")

                quantity = _number(row.get("Quantity"), "quantity")
                unit_price = _number(row.get("Unit_price"), "unit_price")
                discount = _number(row.get("Discount_amount"), "discount_amount")
                if quantity is None:
                    issues.append("missing or invalid quantity")
                elif quantity <= 0:
                    issues.append("quantity must be greater than zero")
                if unit_price is None:
                    issues.append("missing or invalid unit price")
                elif unit_price < 0:
                    issues.append("unit price cannot be negative")
                if discount is None:
                    issues.append("missing or invalid discount")
                elif discount < 0:
                    issues.append("discount cannot be negative")

                status = (row.get("Status") or "").strip()
                transaction_id = (row.get("Transaction_Id") or "").strip()
                for field_name, label in (("Product", "product"), ("Category", "category"),
                                          ("Region", "region"), ("Sales_channel", "sales channel")):
                    if not (row.get(field_name) or "").strip():
                        issues.append(f"missing {label}")
                if quantity is not None and quantity > 0 and unit_price is not None and discount is not None:
                    if discount > quantity * unit_price:
                        issues.append("discount exceeds gross transaction amount")
                if not transaction_id:
                    issues.append("missing transaction id")
                elif transaction_id in seen_transaction_ids:
                    issues.append("duplicate transaction id")
                else:
                    seen_transaction_ids.add(transaction_id)
                if status.lower() != "completed":
                    issues.append(f"status is {status or 'missing'}")

                conn.execute(
                    """INSERT INTO sales_transactions
                    (transaction_id, order_date, product, category, region, sales_channel,
                     quantity, unit_price, discount_amount, status, data_quality_issue)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        transaction_id,
                        order_date,
                        (row.get("Product") or "").strip(),
                        (row.get("Category") or "").strip(),
                        (row.get("Region") or "").strip(),
                        (row.get("Sales_channel") or "").strip(),
                        quantity, unit_price, discount, status,
                        "; ".join(issues) if issues else None,
                    ),
                )
                inserted += 1
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM sales_transactions").fetchone()[0]
        excluded = conn.execute(
            "SELECT COUNT(*) FROM sales_transactions WHERE data_quality_issue IS NOT NULL"
        ).fetchone()[0]
        return {"imported": inserted, "total": total, "excluded_from_revenue": excluded}
    finally:
        conn.close()

def ensure_database(db_path: str | Path = DEFAULT_DB, csv_path: str | Path = DEFAULT_CSV) -> None:
    conn = get_connection(db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sales_transactions'"
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM sales_transactions").fetchone()[0] if exists else 0
    finally:
        conn.close()
    if not exists or count == 0:
        import_csv(csv_path, db_path)
