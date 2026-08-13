import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambdas", "api-reports"))


class ReportReaderTests(unittest.TestCase):
    def test_response_helper_formats_success(self) -> None:
        """Test that _response helper formats 200 success responses correctly."""
        from handler import _response
        
        data = {"run_id": "test-123", "status": "COMPLETED"}
        result = _response(200, data)
        
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["headers"]["Content-Type"], "application/json")
        self.assertIn("test-123", result["body"])

    def test_response_helper_formats_error(self) -> None:
        """Test that _response helper formats error responses correctly."""
        from handler import _response
        
        result = _response(404, {"error": "not_found"})
        
        self.assertEqual(result["statusCode"], 404)
        self.assertIn("not_found", result["body"])

    def test_response_helper_converts_string_to_message(self) -> None:
        """Test that _response helper wraps string bodies in a message dict."""
        from handler import _response
        
        result = _response(500, "Internal error")
        body = json.loads(result["body"])
        
        self.assertEqual(result["statusCode"], 500)
        self.assertEqual(body["message"], "Internal error")

    def test_handler_returns_400_on_missing_run_id(self) -> None:
        """Test that handler returns 400 when runId path parameter is missing."""
        from handler import handler
        
        with patch.dict("os.environ", {"REPORTS_BUCKET": "cip-reports"}):
            result = handler(
                {"pathParameters": None},
                None,
            )
        
        self.assertEqual(result["statusCode"], 400)
        self.assertIn("missing_run_id", result["body"])

    def test_handler_reads_local_report_file_when_present(self) -> None:
        """Test that handler reads reports from the local reports directory."""
        from handler import handler

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "test-123.json"
            report_path.write_text(json.dumps({"run_id": "test-123", "status": "COMPLETED"}), encoding="utf-8")

            with patch.dict("os.environ", {"REPORTS_DIR": tmpdir}, clear=True):
                result = handler({"pathParameters": {"runId": "test-123"}}, None)

            self.assertEqual(result["statusCode"], 200)
            self.assertEqual(json.loads(result["body"])["run_id"], "test-123")

    def test_handler_returns_404_when_local_report_is_missing(self) -> None:
        """Test that handler returns 404 when no local report exists."""
        from handler import handler

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"REPORTS_DIR": tmpdir}, clear=True):
                result = handler({"pathParameters": {"runId": "missing-run"}}, None)

            self.assertEqual(result["statusCode"], 404)
            self.assertIn("not_found", result["body"])


if __name__ == "__main__":
    unittest.main()
