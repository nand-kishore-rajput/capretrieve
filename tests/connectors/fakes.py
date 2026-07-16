"""
Shared test doubles for connector tests. Not a test file itself — no
test_ functions here, just fixtures/fakes that multiple test modules need.
"""

from __future__ import annotations


class FakeTavilyClient:
    """Canned-response stand-in for tavily.TavilyClient. Records the last
    call's arguments so tests can assert on what the connector actually
    sent, without touching the network."""

    def __init__(self, response: dict | None = None) -> None:
        self.response = response if response is not None else {"results": []}
        self.last_query: str | None = None
        self.last_kwargs: dict | None = None

    def search(self, query: str, **kwargs) -> dict:
        self.last_query = query
        self.last_kwargs = kwargs
        return self.response


SAMPLE_TAVILY_RESPONSE = {
    "query": "standing desk back pain research",
    "results": [
        {
            "title": "Standing desks and lower back pain: what the research says",
            "url": "https://example.com/standing-desks",
            "content": "Several studies suggest standing desks reduce reported back pain...",
            "score": 0.91,
        },
        {
            "title": "Ergonomics basics",
            "url": "https://example.com/ergonomics",
            "content": "General ergonomic guidance for office workers...",
            "score": 0.67,
        },
    ],
    "response_time": 1.2,
}