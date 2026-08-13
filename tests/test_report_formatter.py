import unittest

from agentcore.src.orchestrator.graph import _format_report_for_end_user, _build_invoke_response


class ReportFormatterTests(unittest.TestCase):
    def test_format_report_for_end_user_returns_detailed_paragraph(self):
        markdown = """
# Executive Summary
Google remains a strong competitor in the market.
Google remains a strong competitor in the market.

## Risks
A lawsuit is pending against the company.
A lawsuit is pending against the company.
"""

        result = _format_report_for_end_user(markdown, company="Google", country="USA")

        self.assertIn("Google", result)
        self.assertIn("USA", result)
        self.assertIn("Google remains a strong competitor in the market.", result)
        self.assertIn("A lawsuit is pending against the company.", result)
        self.assertNotIn("•", result)

    def test_format_report_for_end_user_removes_bullet_markers_from_plain_lists(self):
        markdown = """
• Apple Strategy and Business Model.
• Tim Cook reactions: Trump, Altman, Buffett on the Apple CEO.
• Product innovation and software-led differentiation remain important growth levers.
"""

        result = _format_report_for_end_user(markdown, company="Apple", country="USA")

        self.assertIn("Apple Strategy and Business Model.", result)
        self.assertIn("Tim Cook reactions: Trump, Altman, Buffett on the Apple CEO.", result)
        self.assertNotIn("•", result)

    def test_format_report_for_end_user_deduplicates_repeated_lead_in_sentence(self):
        markdown = "Apple Strategy and Business Model. Apple Strategy and Business Model. • Tim Cook reactions: Trump, Altman, Buffett on the Apple CEO. • Apple taps John Ternus as CEO to replace Tim Cook, becoming."

        result = _format_report_for_end_user(markdown, company="Apple", country="USA")

        self.assertEqual(result.count("Apple Strategy and Business Model."), 1)
        self.assertIn("Tim Cook reactions: Trump, Altman, Buffett on the Apple CEO.", result)
        self.assertNotIn("•", result)

    def test_report_response_returns_json_payload(self):
        result = _build_invoke_response(
            {
                "run_id": "test-run",
                "company": "Google",
                "country": "USA",
                "tier": "Standard",
                "report": {"markdown": "# Summary\nGoogle is strong."},
            },
            response_mode="report",
            include_debug=False,
        )

        self.assertIsInstance(result, dict)
        self.assertEqual(result["run_id"], "test-run")
        self.assertIn("report", result)
        self.assertIn("Google", result["report"])


if __name__ == "__main__":
    unittest.main()
