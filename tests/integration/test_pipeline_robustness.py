"""
Pipeline robustness tests: fused-item cap wiring, per-source failure
isolation, non-blocking LLM calls, and the /trace/view CSP header.

Uses stub connectors over the real manifests, so these run without
fixtures/data/ (unlike test_api.py, which needs the sample vault/corpus).
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from capretrieve.api.app import create_app
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.graph.build import build_graph
from capretrieve.registry.static import build_registry

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"
TOKEN = "test-token"


class StubConnector:
    def __init__(self, manifest, n_results: int = 0, error: Exception | None = None):
        self._manifest = manifest
        self._n_results = n_results
        self._error = error

    def manifest(self):
        return self._manifest

    async def retrieve(self, req) -> RetrievalResult:
        if self._error is not None:
            raise self._error
        cid = self._manifest.connector_id
        return RetrievalResult(
            evidence=[
                Evidence(
                    source_id=cid,
                    content=f"{cid} result {i}",
                    score=float(self._n_results - i),
                    uri=f"{cid}://{i}",
                    retrieved_at=datetime.now(timezone.utc),
                )
                for i in range(self._n_results)
            ]
        )

    async def health(self) -> HealthStatus:
        return HealthStatus(state=HealthState.OK)


class FakeLLMClient:
    def __init__(self, response: str, delay_s: float = 0.0) -> None:
        self.response = response
        self.delay_s = delay_s
        self.calls = 0

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls += 1
        if self.delay_s:
            time.sleep(self.delay_s)  # a blocking call, like the real httpx.post
        return self.response


def _requirements_json(**overrides) -> str:
    fields = {
        "paradigm_hint": "dense_semantic",
        "relational": False,
        "needs_freshness": "any",
        "privacy_sensitivity": "none",
        "expects_personal_knowledge": False,
        "seed_entity": None,
    }
    fields.update(overrides)
    return json.dumps(fields)


def _registry(chroma=None, obsidian=None, web=None):
    registry = build_registry(CONFIG_DIR)
    manifests = registry.manifests()
    registry.register(chroma or StubConnector(manifests["chroma"], n_results=3))
    registry.register(obsidian or StubConnector(manifests["obsidian"], n_results=3))
    registry.register(web or StubConnector(manifests["web_search"], n_results=3))
    return registry


def test_create_app_applies_max_fused_items():
    app = create_app(
        _registry(),
        FakeLLMClient(_requirements_json()),
        FakeLLMClient("answer"),
        max_fused_items=1,
    )
    resp = TestClient(app).post("/query", json={"query": "q", "top_k": 3})

    assert resp.status_code == 200
    assert len(resp.json()["evidence"]) == 1


def test_failing_source_does_not_fail_the_query():
    manifests = build_registry(CONFIG_DIR).manifests()
    broken = StubConnector(manifests["obsidian"], error=RuntimeError("vault offline"))
    app = create_app(
        _registry(obsidian=broken),
        # personal knowledge -> both local sources are selected
        FakeLLMClient(_requirements_json(expects_personal_knowledge=True)),
        FakeLLMClient("answer"),
    )
    resp = TestClient(app).post("/query", json={"query": "my notes on q", "top_k": 3})

    assert resp.status_code == 200
    data = resp.json()
    assert {ev["source_id"] for ev in data["evidence"]} == {"chroma"}
    records = {r["connector_id"]: r for r in data["plan_trace"]["execution"]}
    assert "vault offline" in records["obsidian"]["error"]
    assert records["chroma"]["error"] is None


def test_trace_view_shows_source_error_and_sets_csp():
    manifests = build_registry(CONFIG_DIR).manifests()
    broken = StubConnector(manifests["obsidian"], error=RuntimeError("vault offline"))
    app = create_app(
        _registry(obsidian=broken),
        FakeLLMClient(_requirements_json(expects_personal_knowledge=True)),
        FakeLLMClient("answer"),
        trace_view_token=TOKEN,
    )
    resp = TestClient(app).get("/trace/view", params={"query": "my notes on q", "token": TOKEN})

    assert resp.status_code == 200
    assert "vault offline" in resp.text
    assert resp.headers["content-security-policy"].startswith("default-src 'none'")


@pytest.mark.asyncio
async def test_llm_calls_do_not_block_concurrent_queries():
    """Each query makes two 0.3s blocking LLM calls. If they ran on the
    event loop, two concurrent queries would take ~1.2s; off-loop, ~0.6s."""
    graph = build_graph(
        _registry(),
        FakeLLMClient(_requirements_json(), delay_s=0.3),
        FakeLLMClient("answer", delay_s=0.3),
    )

    start = time.perf_counter()
    await asyncio.gather(
        graph.ainvoke({"query": "a", "top_k": 3}),
        graph.ainvoke({"query": "b", "top_k": 3}),
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0


def _trace_view_app(token: str | None = TOKEN):
    analyzer = FakeLLMClient(_requirements_json())
    app = create_app(_registry(), analyzer, FakeLLMClient("answer"), trace_view_token=token)
    return TestClient(app), analyzer


@pytest.mark.parametrize("params", [{}, {"token": "wrong-token"}])
def test_trace_view_rejects_missing_or_wrong_token_before_any_llm_call(params):
    client, analyzer = _trace_view_app()

    resp = client.get("/trace/view", params={"query": "q", **params})

    assert resp.status_code == 403
    assert analyzer.calls == 0


def test_trace_view_is_disabled_when_no_token_is_configured():
    client, analyzer = _trace_view_app(token=None)

    resp = client.get("/trace/view", params={"query": "q", "token": ""})

    assert resp.status_code == 403
    assert analyzer.calls == 0


def test_trace_view_accepts_the_configured_token():
    client, _ = _trace_view_app()

    resp = client.get("/trace/view", params={"query": "q", "token": TOKEN})

    assert resp.status_code == 200


@pytest.mark.parametrize("top_k", [0, 51, 100000])
def test_trace_view_rejects_out_of_range_top_k(top_k):
    client, analyzer = _trace_view_app()

    resp = client.get("/trace/view", params={"query": "q", "token": TOKEN, "top_k": top_k})

    assert resp.status_code == 422
    assert analyzer.calls == 0


@pytest.mark.parametrize("top_k", [0, 51, 100000])
def test_query_rejects_out_of_range_top_k(top_k):
    analyzer = FakeLLMClient(_requirements_json())
    client = TestClient(create_app(_registry(), analyzer, FakeLLMClient("answer")))

    resp = client.post("/query", json={"query": "q", "top_k": top_k})

    assert resp.status_code == 422
    assert analyzer.calls == 0
