import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_ai_status_does_not_expose_credentials(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "auto", "GEMINI_API_KEY": "secret-g", "GROQ_API_KEY": "secret-q"}):
            response = self.client.get("/ai-status")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["gemini_configured"])
        self.assertTrue(response.json()["groq_configured"])
        self.assertNotIn("secret", response.text)

    def test_schema_endpoint_discovers_database(self):
        response = self.client.get("/schema")
        self.assertEqual(response.status_code, 200)
        self.assertIn("sales_transactions", {t["name"] for t in response.json()["tables"]})

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_dynamic_question_returns_sql_rows_and_chart(self):
        plan = {"sql": "SELECT region, SUM(quantity * unit_price - discount_amount) AS revenue FROM sales_transactions WHERE data_quality_issue IS NULL GROUP BY region ORDER BY revenue DESC", "parameters": [], "chart_type": "bar", "title": "Revenue by region", "x_key": "region", "y_keys": ["revenue"]}
        summary = {"answer": "North has the highest revenue in the returned data.", "insights": ["The result compares regions."], "limitations": ""}
        with patch("backend.main.generate_sql", return_value=(plan, "Gemini")), patch("backend.main.summarize_results", return_value=(summary, "Gemini")):
            response = self.client.post("/ask", json={"question": "Which region generated most revenue?"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn("SELECT", body["sql"].upper())
        self.assertTrue(body["rows"])
        self.assertIn("chart", body)
        self.assertEqual(body["execution_source"], "Local SQLite (read-only)")

    def test_ai_unavailable_returns_clear_error(self):
        with patch("backend.main.generate_sql", return_value=(None, "unavailable")):
            response = self.client.post("/ask", json={"question": "How many transactions are there?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("GEMINI_API_KEY", response.json()["detail"])

    def test_unsupported_question_is_reported_from_schema(self):
        plan = {"sql": "", "chart_type": "table", "title": "", "x_key": "", "y_keys": []}
        with patch("backend.main.generate_sql", return_value=(plan, "Gemini")):
            response = self.client.post("/ask", json={"question": "What is the weather on Mars?"})
        self.assertEqual(response.status_code, 422)

    def test_blank_question_is_rejected(self):
        response = self.client.post("/ask", json={"question": "  "})
        self.assertEqual(response.status_code, 422)

    def test_overlong_question_is_rejected(self):
        response = self.client.post("/ask", json={"question": "x" * 1001})
        self.assertEqual(response.status_code, 422)

    def test_invalid_request_shape_is_rejected(self):
        response = self.client.post("/ask", json={"not_question": "hello"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
