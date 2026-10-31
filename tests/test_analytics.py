import csv
import tempfile
import unittest
from pathlib import Path

from backend.database import import_csv, get_connection
from backend import analytics

CSV = Path(__file__).resolve().parents[1] / "data" / "sales_data.csv"


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        import_csv(CSV, self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_total_revenue_returns_numeric_value(self):
        result = analytics.total_revenue(db_path=self.db)
        self.assertGreater(result["metrics"]["total_revenue"], 0)
        self.assertEqual(result["intent"], "total_revenue")

    def test_top_product_has_product_and_revenue(self):
        result = analytics.top_product(db_path=self.db)
        self.assertTrue(result["metrics"]["product"])
        self.assertGreater(result["metrics"]["revenue"], 0)

    def test_monthly_trend_is_ordered(self):
        result = analytics.monthly_trend(db_path=self.db)
        months = [row["month"] for row in result["supporting_data"]]
        self.assertEqual(months, sorted(months))
        self.assertGreaterEqual(len(months), 1)

    def test_top_region_returns_region(self):
        result = analytics.top_region(db_path=self.db)
        self.assertIn(result["metrics"]["region"], {"North", "South", "East", "West"})

    def test_month_comparison_has_two_months(self):
        result = analytics.month_comparison("2026-01", "2026-02", db_path=self.db)
        self.assertEqual(result["metrics"]["month1"], "2026-01")
        self.assertEqual(result["metrics"]["month2"], "2026-02")

    def test_missing_month_comparison_is_zero_not_crash(self):
        result = analytics.month_comparison("2025-01", "2025-02", db_path=self.db)
        self.assertEqual(result["metrics"]["revenue1"], 0)
        self.assertEqual(result["metrics"]["revenue2"], 0)

    def test_fractional_quantity_is_marked_invalid_and_excluded(self):
        source = Path(self.temp.name) / "fractional.csv"
        with source.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Transaction_Id", "Order_date", "Product", "Category", "Region",
                "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
            ])
            writer.writeheader()
            writer.writerow({"Transaction_Id":"T1", "Order_date":"01-01-2026", "Product":"P",
                "Category":"C", "Region":"North", "Sales_channel":"Online", "Quantity":"2.5",
                "Unit_price":"100", "Discount_amount":"0", "Status":"Completed"})
        db = Path(self.temp.name) / "fractional.db"
        import_csv(source, db)
        quality = analytics.data_quality(db)
        self.assertEqual(quality["summary"]["excluded_rows"], 1)
        self.assertEqual(analytics.total_revenue(db_path=db)["metrics"]["total_revenue"], 0)

    def test_missing_required_csv_column_is_rejected(self):
        source = Path(self.temp.name) / "bad.csv"
        source.write_text("Transaction_Id,Order_date\nT1,01-01-2026\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            import_csv(source, Path(self.temp.name) / "bad.db")

    def test_missing_discount_is_excluded_instead_of_assumed_zero(self):
        source = Path(self.temp.name) / "missing_discount.csv"
        with source.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Transaction_Id", "Order_date", "Product", "Category", "Region",
                "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
            ])
            writer.writeheader()
            writer.writerow({"Transaction_Id":"T2", "Order_date":"01-01-2026", "Product":"P",
                "Category":"C", "Region":"North", "Sales_channel":"Online", "Quantity":"2",
                "Unit_price":"100", "Discount_amount":"", "Status":"Completed"})
        db = Path(self.temp.name) / "missing_discount.db"
        import_csv(source, db)
        self.assertEqual(analytics.total_revenue(db_path=db)["metrics"]["total_revenue"], 0)

    def test_duplicate_transaction_ids_are_retained_but_excluded(self):
        source = Path(self.temp.name) / "duplicates.csv"
        fields = ["Transaction_Id", "Order_date", "Product", "Category", "Region",
                  "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"]
        with source.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            row = {"Transaction_Id":"DUP", "Order_date":"01-01-2026", "Product":"P",
                   "Category":"C", "Region":"North", "Sales_channel":"Online", "Quantity":"1",
                   "Unit_price":"100", "Discount_amount":"0", "Status":"Completed"}
            writer.writerow(row)
            writer.writerow(row)
        db = Path(self.temp.name) / "duplicates.db"
        summary = import_csv(source, db)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["excluded_from_revenue"], 1)
        self.assertEqual(analytics.total_revenue(db_path=db)["metrics"]["total_revenue"], 100)

    def test_non_finite_unit_price_is_rejected(self):
        source = Path(self.temp.name) / "nan_price.csv"
        fields = ["Transaction_Id", "Order_date", "Product", "Category", "Region",
                  "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"]
        with source.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow({"Transaction_Id":"NAN", "Order_date":"01-01-2026", "Product":"P",
                "Category":"C", "Region":"North", "Sales_channel":"Online", "Quantity":"1",
                "Unit_price":"NaN", "Discount_amount":"0", "Status":"Completed"})
        db = Path(self.temp.name) / "nan.db"
        import_csv(source, db)
        self.assertEqual(analytics.data_quality(db)["summary"]["excluded_rows"], 1)
        self.assertEqual(analytics.total_revenue(db_path=db)["metrics"]["total_revenue"], 0)

    def test_failed_import_does_not_erase_previous_database_rows(self):
        bad = Path(self.temp.name) / "bad_after_good.csv"
        bad.write_text("Transaction_Id,Order_date\nX,01-01-2026\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            import_csv(bad, self.db)
        # The import transaction is rolled back; the previously imported data remains.
        self.assertGreater(analytics.total_revenue(db_path=self.db)["metrics"]["total_revenue"], 0)


if __name__ == "__main__":
    unittest.main()
