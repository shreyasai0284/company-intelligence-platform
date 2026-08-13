import unittest

from agentcore.agents._cache import _build_searchable_text, _build_vector_document


class RetrievalLayerTests(unittest.TestCase):
    def test_build_searchable_text_flattens_nested_payload(self) -> None:
        payload = {
            "company": "Tesla",
            "profile": {
                "summary": "Tesla faces regulatory scrutiny.",
                "sources": [{"title": "Reuters Tesla probe"}],
            },
            "recent_headlines": [
                "Tesla faces regulatory scrutiny.",
                "Recall expands after safety probe",
            ],
        }

        searchable_text = _build_searchable_text(payload)

        self.assertIn("Tesla", searchable_text)
        self.assertIn("Tesla faces regulatory scrutiny.", searchable_text)
        self.assertIn("Recall expands after safety probe", searchable_text)
        self.assertEqual(searchable_text.count("Tesla faces regulatory scrutiny."), 1)

    def test_build_vector_document_includes_lookup_metadata(self) -> None:
        payload = {
            "company": "Tesla",
            "country": "US",
            "profile": {"summary": "Tesla faces regulatory scrutiny."},
        }

        document = _build_vector_document("TESLA:US:RESEARCH", payload, ttl_seconds=60)

        self.assertEqual(document["cache_key"], "TESLA:US:RESEARCH")
        self.assertEqual(document["company"], "Tesla")
        self.assertEqual(document["country"], "US")
        self.assertEqual(document["domain"], "RESEARCH")
        self.assertIn("searchable_text", document)
        self.assertGreater(document["ttl"], document["updated_at"])


if __name__ == "__main__":
    unittest.main()