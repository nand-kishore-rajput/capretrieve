"""
GET /demo: a browser page with a question box that calls POST /query and
renders the decisions, trace and answer. Uses stub connectors over the
real manifests, so it runs without fixtures/data/.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from capretrieve.api.app import create_app
from capretrieve.api.routes.demo import DEMO_JS
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.registry.static import build_registry

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"


class StubConnector:
    def __init__(self, manifest):
        self._manifest = manifest

    def manifest(self):
        return self._manifest

    async def retrieve(self, req) -> RetrievalResult:
        cid = self._manifest.connector_id
        return RetrievalResult(
            evidence=[
                Evidence(
                    source_id=cid,
                    content=f"{cid} result",
                    score=1.0,
                    uri=f"{cid}://0",
                    retrieved_at=datetime.now(timezone.utc),
                )
            ]
        )

    async def health(self) -> HealthStatus:
        return HealthStatus(state=HealthState.OK)


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls += 1
        return self.response


def _client():
    registry = build_registry(CONFIG_DIR)
    for manifest in registry.manifests().values():
        registry.register(StubConnector(manifest))
    analyzer = FakeLLMClient(
        json.dumps(
            {
                "paradigm_hint": "dense_semantic",
                "relational": False,
                "needs_freshness": "any",
                "privacy_sensitivity": "none",
                "expects_personal_knowledge": False,
                "seed_entity": None,
            }
        )
    )
    app = create_app(registry, analyzer, FakeLLMClient("answer"))
    return TestClient(app), analyzer


def test_demo_page_serves_a_question_form_without_calling_the_llm():
    client, analyzer = _client()

    resp = client.get("/demo")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "<textarea" in resp.text
    assert 'src="/demo.js"' in resp.text
    assert analyzer.calls == 0


def test_demo_page_allows_only_its_own_script():
    client, _ = _client()

    csp = client.get("/demo").headers["content-security-policy"]

    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "unsafe-inline" not in csp.split("script-src", 1)[1].split(";")[0]


def test_demo_script_is_served_and_posts_to_query():
    client, _ = _client()

    resp = client.get("/demo.js")

    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
    assert '"/query"' in resp.text


def test_demo_script_never_injects_html():
    """Query text, evidence and answers are rendered as text, not markup."""
    assert "innerHTML" not in DEMO_JS
    assert "outerHTML" not in DEMO_JS
    assert "insertAdjacentHTML" not in DEMO_JS
