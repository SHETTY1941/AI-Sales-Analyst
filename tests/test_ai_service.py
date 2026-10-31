import os
import unittest
from unittest.mock import patch
from backend.ai_service import generate_sql, ai_status


class AIServiceTests(unittest.TestCase):
    def setUp(self):
        self.schema = {"tables": [{"name": "sales_transactions", "columns": [
            {"name": "region", "type": "TEXT"}, {"name": "quantity", "type": "INTEGER"}
        ]}]}

    def test_gemini_returns_dynamic_sql_plan(self):
        fake = {"candidates": [{"content": {"parts": [{"text": '{"sql":"SELECT region FROM sales_transactions WHERE region = ?","parameters":["South"],"chart_type":"bar","title":"South sales","x_key":"region","y_keys":[]}'}]}}]}
        with patch.dict(os.environ, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}), \
             patch("backend.ai_service._post_json", return_value=fake):
            plan, provider = generate_sql("Show South region", self.schema)
        self.assertEqual(provider, "Gemini")
        self.assertEqual(plan["parameters"], ["South"])
        self.assertIn("?", plan["sql"])

    def test_auto_uses_groq_when_gemini_key_missing(self):
        fake = {"choices": [{"message": {"content": '{"sql":"SELECT COUNT(*) AS order_count FROM sales_transactions","parameters":[],"chart_type":"number","title":"Orders","x_key":"","y_keys":["order_count"]}'}}]}
        with patch.dict(os.environ, {"AI_PROVIDER": "auto", "GEMINI_API_KEY": "", "GROQ_API_KEY": "groq-test"}), \
             patch("backend.ai_service._post_json", return_value=fake):
            plan, provider = generate_sql("How many orders?", self.schema)
        self.assertEqual(provider, "Groq")
        self.assertEqual(plan["chart_type"], "number")

    def test_placeholder_api_keys_are_not_treated_as_configured(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GROQ_API_KEY": "YOUR_NEW_GROQ_KEY"}):
            status = ai_status()
        self.assertFalse(status["gemini_configured"])
        self.assertFalse(status["groq_configured"])

    def test_invalid_parameter_types_are_rejected(self):
        fake = {"candidates": [{"content": {"parts": [{"text": '{"sql":"SELECT 1","parameters":[{"unsafe":"object"}],"chart_type":"number"}'}]}}]}
        with patch.dict(os.environ, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "test"}), \
             patch("backend.ai_service._post_json", return_value=fake):
            plan, _ = generate_sql("Return one", self.schema)
        self.assertIsNone(plan)


if __name__ == "__main__":
    unittest.main()
