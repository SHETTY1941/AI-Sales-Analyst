import unittest
from backend.query_engine import discover_schema, validate_and_execute, chart_metadata


class QueryEngineTests(unittest.TestCase):
    def test_schema_discovery_lists_sales_columns(self):
        schema = discover_schema()
        names = {table["name"] for table in schema["tables"]}
        self.assertIn("sales_transactions", names)
        sales = next(t for t in schema["tables"] if t["name"] == "sales_transactions")
        columns = {column["name"] for column in sales["columns"]}
        self.assertIn("quantity", columns)
        self.assertIn("discount_amount", columns)

    def test_select_query_executes_locally(self):
        rows, columns, sql = validate_and_execute(
            "SELECT region, SUM(quantity * unit_price - discount_amount) AS revenue "
            "FROM sales_transactions WHERE data_quality_issue IS NULL GROUP BY region ORDER BY revenue DESC"
        )
        self.assertTrue(rows)
        self.assertIn("region", columns)
        self.assertIn("revenue", columns)
        self.assertIn("SELECT", sql.upper())

    def test_filter_values_are_bound_as_parameters(self):
        rows, columns, _ = validate_and_execute(
            "SELECT product FROM sales_transactions WHERE region = ? AND data_quality_issue IS NULL LIMIT 5",
            ["North"],
        )
        self.assertIn("product", columns)
        self.assertTrue(all(row["product"] for row in rows))

    def test_write_query_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_and_execute("DELETE FROM sales_transactions")

    def test_multi_statement_query_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_and_execute("SELECT 1; SELECT 2")

    def test_internal_table_access_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_and_execute("SELECT name FROM sqlite_master")

    def test_chart_metadata_infers_numeric_series(self):
        chart = chart_metadata({"chart_type": "bar", "x_key": "region", "y_keys": ["revenue"]},
                               [{"region": "North", "revenue": 123.0}], ["region", "revenue"])
        self.assertEqual(chart["type"], "number")
        self.assertEqual(chart["y_keys"], ["revenue"])


if __name__ == "__main__":
    unittest.main()
