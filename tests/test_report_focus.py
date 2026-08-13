import unittest
from unittest.mock import patch

from agentcore.src.processing.impact import rank_text_items
from agentcore.src.processing.synthesis import synthesize
from agentcore.src.reports import generator


class ReportFocusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validated = {
            "research": {"profile": {"summary": "Tesla faces close scrutiny over production execution."}},
            "news": {
                "articles": [
                    "Tesla faces federal safety probe after recall expansion",
                    "Tesla opens new showroom in a regional market",
                ],
                "sentiment_score": -0.35,
            },
            "litigation": {
                "cases": ["Class action lawsuit alleges autopilot marketing misstatements"],
                "active_count": 1,
            },
            "leadership": {
                "executives": ["CFO reiterates cost controls"],
                "product_lines": ["Updated Model lineup planned"],
            },
            "financial": {
                "ticker": "TSLA",
                "share_price": "$250.00",
                "cagr_5y": 12.5,
                "corporate_brief": "Revenue growth remains positive but margins are under pressure.",
            },
        }

    def test_synthesis_separates_material_news_and_litigation(self) -> None:
        synthesized = synthesize(self.validated)

        self.assertEqual(
            synthesized["news"]["material_articles"],
            ["Tesla faces federal safety probe after recall expansion"],
        )
        self.assertEqual(
            synthesized["news"]["contextual_articles"],
            ["Tesla opens new showroom in a regional market"],
        )
        self.assertEqual(
            synthesized["litigation"]["material_cases"],
            ["Class action lawsuit alleges autopilot marketing misstatements"],
        )
        self.assertGreater(
            synthesized["news"]["ranked_articles"][0]["impact_score"],
            synthesized["news"]["ranked_articles"][1]["impact_score"],
        )

    def test_local_report_prefers_material_items(self) -> None:
        synthesized = synthesize(self.validated)

        with patch.object(generator, "_candidate_models", return_value=[]):
            report = generator.generate_report(
                tier="Premium",
                company="Tesla",
                country="US",
                synthesized=synthesized,
            )

        markdown = report["markdown"]
        self.assertIn("Material negative or high-impact news", markdown)
        self.assertIn("Material litigation or regulatory risk", markdown)
        self.assertNotIn("new showroom", markdown.lower())

        summary_section = markdown.split("## Profile", 1)[0].lower()
        self.assertNotIn("showroom", summary_section)
        self.assertNotIn("updated model", summary_section)

    def test_ranker_orders_negative_before_positive(self) -> None:
        ranked = rank_text_items(
            [
                "Company opens a new showroom in a regional market",
                "Company faces federal safety probe after recall expansion",
            ],
            domain="news",
        )

        self.assertEqual(ranked[0]["polarity"], "negative")
        self.assertIn("probe", ranked[0]["reasons"])


if __name__ == "__main__":
    unittest.main()