import unittest

from fastapi.testclient import TestClient

from local_backend import app, build_status_result_payload


class LocalBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_ping_route(self) -> None:
        response = self.client.get('/ping')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_invocations_route_accepts_payload(self) -> None:
        response = self.client.post('/invocations', json={
            'company': 'Apple',
            'country': 'USA',
            'tier': 'Standard',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('run_id', response.json())

    def test_build_status_result_payload_normalizes_agent_cards(self) -> None:
        payload = build_status_result_payload(
            {
                'research': {
                    'profile': {
                        'summary': 'Contoso operates across global markets.',
                        'sources': [{'title': 'Annual Report'}],
                    }
                },
                'news': {
                    'recent_headlines': ['Contoso expands into Europe'],
                    'sentiment_score': 0.82,
                },
                'litigation': {
                    'active_count': 2,
                    'cases': ['Case A', 'Case B'],
                },
                'leadership': {
                    'executives_updates': ['New CFO appointed'],
                    'product_lines_updates': ['New product launch'],
                },
                'financial': {
                    'corporate_brief': 'Revenue growth remains healthy.',
                    'ticker': 'CTSO',
                    'share_price': '$12.00',
                    'cagr_5y': 8.4,
                },
                'report': {'markdown': 'Executive summary text'},
            },
            run_id='demo-run',
            company='Contoso',
            country='US',
            tier='Standard',
            created_at='2026-01-01T00:00:00Z',
            completed_at='2026-01-01T00:01:00Z',
        )

        self.assertEqual(payload['executive_summary'], 'Executive summary text')
        self.assertIn('research', payload['agent_results'])
        self.assertEqual(payload['agent_results']['research']['title'], 'Research Profile')
        self.assertIn('global markets', payload['agent_results']['research']['detailed_insight'])
        self.assertIn('news', payload['agent_results'])
        self.assertIn('Litigation', payload['agent_results']['litigation']['title'])
        self.assertIn('financial', payload['agent_results'])

    def test_build_status_result_payload_filters_out_irrelevant_company_evidence(self) -> None:
        payload = build_status_result_payload(
            {
                'research': {
                    'profile': {
                        'summary': 'Apple is expanding its services business.',
                        'sources': [{'title': 'Apple annual report'}],
                    }
                },
                'news': {
                    'recent_headlines': ['• Apple expands in Europe', 'Tesla has avoided a formal defect investigation.'],
                    'sentiment_score': 0.24,
                },
                'litigation': {
                    'active_count': 1,
                    'cases': ['Apple faces a class action over App Store practices.'],
                },
                'leadership': {
                    'executives_updates': ['Apple appoints a new finance lead.'],
                    'product_lines_updates': ['Apple launches a new iPhone model.'],
                },
                'financial': {
                    'corporate_brief': 'Apple remains financially strong.',
                    'ticker': 'AAPL',
                    'share_price': '$200.00',
                    'cagr_5y': 12.3,
                },
                'report': {'markdown': 'Apple summary text'},
            },
            run_id='demo-run',
            company='Apple',
            country='US',
            tier='Standard',
            created_at='2026-01-01T00:00:00Z',
            completed_at='2026-01-01T00:01:00Z',
        )

        news_evidence = payload['agent_results']['news']['system_evidence']
        self.assertEqual(news_evidence, ['Apple expands in Europe.'])
        litigation_evidence = payload['agent_results']['litigation']['system_evidence']
        self.assertIn('Apple faces a class action over App Store practices.', litigation_evidence)
        self.assertIn('Apple remains financially strong.', payload['agent_results']['financial']['system_evidence'])

    def test_build_status_result_payload_cleans_malformed_evidence_text(self) -> None:
        payload = build_status_result_payload(
            {
                'research': {
                    'profile': {
                        'summary': 'Apple is expanding its services business.',
                        'sources': [{'title': 'Apple annual report'}],
                    }
                },
                'news': {
                    'recent_headlines': ['Apple expands in Europe | | ...', 'Tesla has avoided a formal defect investigation.'],
                    'sentiment_score': 0.24,
                },
                'litigation': {
                    'active_count': 1,
                    'cases': ['Apple faces a class action over App Store practices.'],
                },
                'leadership': {
                    'executives_updates': ['Apple appoints a new finance lead...'],
                    'product_lines_updates': ['| | Apple launches a new iPhone model'],
                },
                'financial': {
                    'corporate_brief': 'Apple remains financially strong...',
                    'ticker': 'AAPL',
                },
                'report': {'markdown': 'Apple summary text'},
            },
            run_id='demo-run',
            company='Apple',
            country='US',
            tier='Standard',
            created_at='2026-01-01T00:00:00Z',
            completed_at='2026-01-01T00:01:00Z',
        )

        leadership_evidence = payload['agent_results']['leadership']['system_evidence']
        self.assertIn('Apple appoints a new finance lead.', leadership_evidence)
        self.assertIn('Apple launches a new iPhone model.', leadership_evidence)
        self.assertEqual(payload['agent_results']['financial']['system_evidence'], ['Apple remains financially strong.'])

    def test_build_status_result_payload_keeps_financial_evidence_from_ticker_brief(self) -> None:
        payload = build_status_result_payload(
            {
                'research': {'profile': {'summary': 'Microsoft is a large software company.', 'sources': []}},
                'news': {'recent_headlines': [], 'sentiment_score': 0.3},
                'litigation': {'active_count': 0, 'cases': []},
                'leadership': {'executives_updates': [], 'product_lines_updates': []},
                'financial': {
                    'corporate_brief': 'Ticker MSFT market value at $451.22 with computed CAGR of 12.42%.',
                    'ticker': 'MSFT',
                    'share_price': '$451.22',
                    'cagr_5y': 12.42,
                },
                'report': {'markdown': 'Microsoft summary text'},
            },
            run_id='demo-run',
            company='Microsoft',
            country='US',
            tier='Standard',
            created_at='2026-01-01T00:00:00Z',
            completed_at='2026-01-01T00:01:00Z',
        )

        self.assertIn('Ticker MSFT market value at $451.22 with computed CAGR of 12.42%.', payload['agent_results']['financial']['system_evidence'])


if __name__ == '__main__':
    unittest.main()
