"""
Integration tests for api/app.py — using FastAPI's TestClient (in-process,
no real server or network) with real Obsidian/Chroma connectors and fake
web/LLM clients, same setup as tests/integration/test_graph_pipeline.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
import pytest
from fastapi.testclient import TestClient

from capretrieve.api.app import create_app
from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.connectors.obsidian.connector import ObsidianConnector
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.result import RetrievalResult
from capretrieve.registry.static import build_registry

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"
VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"
CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self.response = response

    def complete(self, messages: list[dict], **kwargs) -> str:
        return self.response


class FakeWebConnector:
    def __init__(self, manifest, evidence=None):
        self._manifest = manifest
        self._evidence = evidence if evidence is not None else []

    def manifest(self):
        return self._manifest

    async def retrieve(self, req) -> RetrievalResult:
        return RetrievalResult(evidence=self._evidence)

    async def health(self) -> HealthStatus:
        return HealthStatus(state=HealthState.OK)


def _requirements_json(**overrides) -> str:
    defaults = {
        "paradigm_hint": "unknown",
        "relational": False,
        "needs_freshness": "any",
        "privacy_sensitivity": "none",
        "expects_personal_knowledge": False,
    }
    defaults.update(overrides)
    return json.dumps(defaults)


@pytest.fixture
def client() -> TestClient:
    registry = build_registry(CONFIG_DIR)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=VAULT_DIR)
    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    ef = HashingEmbeddingFunction()
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name="api_test", embedding_function=ef)
    chroma = ChromaConnector(
        manifest=manifests["chroma"], client=chroma_client, collection_name="api_test", embedding_function=ef
    )
    web = FakeWebConnector(manifests["web_search"])

    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)

    analyzer_client = FakeLLMClient(
        _requirements_json(paradigm_hint="dense_semantic", expects_personal_knowledge=False)
    )
    synthesis_client = FakeLLMClient("Intermittent fasting seems to help with energy [1].")

    app = create_app(registry, analyzer_client, synthesis_client)
    return TestClient(app)


@pytest.fixture
def personal_client() -> TestClient:
    """A separate fixture for tests that exercise personal-knowledge routing
    (expects_personal_knowledge=True), which correctly selects both local
    connectors."""
    registry = build_registry(CONFIG_DIR)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=VAULT_DIR)
    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    ef = HashingEmbeddingFunction()
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name="api_personal_test", embedding_function=ef)
    chroma = ChromaConnector(
        manifest=manifests["chroma"], client=chroma_client, collection_name="api_personal_test", embedding_function=ef
    )
    web = FakeWebConnector(manifests["web_search"])

    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)

    analyzer_client = FakeLLMClient(
        _requirements_json(paradigm_hint="dense_semantic", expects_personal_knowledge=True)
    )
    synthesis_client = FakeLLMClient("Based on your notes, fasting helps with energy [1][2].")

    app = create_app(registry, analyzer_client, synthesis_client)
    return TestClient(app)


def test_get_connectors_returns_all_three_manifests(client: TestClient):
    resp = client.get("/connectors")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["connectors"].keys()) == {"obsidian", "chroma", "web_search"}


def test_get_connectors_manifest_shape(client: TestClient):
    resp = client.get("/connectors")
    web_manifest = resp.json()["connectors"]["web_search"]
    assert web_manifest["query_leaks_externally"] is True
    assert web_manifest["paradigm"] == "keyword"


def test_get_health_returns_all_three_connectors(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    connector_ids = {entry["connector_id"] for entry in data["connectors"]}
    assert connector_ids == {"obsidian", "chroma", "web_search"}


def test_get_health_reports_ok_states(client: TestClient):
    resp = client.get("/health")
    data = resp.json()
    for entry in data["connectors"]:
        assert entry["health"]["state"] in {"ok", "degraded", "down"}


def test_post_query_returns_answer_evidence_and_trace(client: TestClient):
    resp = client.post(
        "/query",
        json={"query": "Summarize what my notes say about intermittent fasting.", "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "answer" in data
    assert "evidence" in data
    assert "plan_trace" in data
    assert data["answer"] == "Intermittent fasting seems to help with energy [1]."


def test_post_query_selects_only_chroma_for_semantic_query(client: TestClient):
    """A general (non-personal) semantic query should route to chroma alone.
    Note: queries phrased as 'my notes' trigger expects_personal_knowledge=True,
    which now correctly also selects obsidian. This test uses a general
    phrasing to isolate S5 (chroma-only) behaviour."""
    resp = client.post(
        "/query",
        json={"query": "What does the literature say about intermittent fasting?", "top_k": 3},
    )
    data = resp.json()
    selected = [s["connector_id"] for s in data["plan_trace"]["execution_plan"]["steps"]]
    assert selected == ["chroma"]


def test_post_query_personal_knowledge_selects_both_local_connectors(
    personal_client: TestClient,
):
    """When expects_personal_knowledge=True, the force-include policy
    should select both private_local connectors (chroma + obsidian)
    regardless of their relative scores. This is the fix for the real
    bug found in live testing: 'summarize my personal notes on X' was
    only returning chroma results despite obsidian having the user's
    own vault notes."""
    resp = personal_client.post(
        "/query",
        json={"query": "summarize my personal notes on intermittent fasting", "top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    selected = {s["connector_id"] for s in data["plan_trace"]["execution_plan"]["steps"]}
    assert selected == {"chroma", "obsidian"}
    sources_in_evidence = {ev["source_id"] for ev in data["evidence"]}
    assert "obsidian" in sources_in_evidence


def test_post_query_evidence_has_source_and_uri(client: TestClient):
    """Evidence items must have a source_id and uri regardless of which
    connector(s) were selected."""
    resp = client.post(
        "/query",
        json={"query": "What does the literature say about intermittent fasting?", "top_k": 3},
    )
    data = resp.json()
    assert len(data["evidence"]) > 0
    for ev in data["evidence"]:
        assert ev["source_id"] in {"chroma", "obsidian"}
        assert ev["uri"] is not None


def test_post_query_missing_query_field_returns_422(client: TestClient):
    resp = client.post("/query", json={"top_k": 3})
    assert resp.status_code == 422


def test_post_query_defaults_top_k(client: TestClient):
    resp = client.post(
        "/query", json={"query": "Summarize what my notes say about intermittent fasting."}
    )
    assert resp.status_code == 200


def test_get_trace_view_returns_html_page(client: TestClient):
    resp = client.get(
        "/trace/view",
        params={"query": "What does the literature say about intermittent fasting?", "top_k": 3},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_get_trace_view_shows_query_selection_and_answer(client: TestClient):
    resp = client.get(
        "/trace/view",
        params={"query": "What does the literature say about intermittent fasting?"},
    )
    body = resp.text
    assert "What does the literature say about intermittent fasting?" in body
    assert "<strong>Selected:</strong> chroma</p>" in body
    assert "Intermittent fasting seems to help with energy [1]." in body


def test_get_trace_view_missing_query_returns_422(client: TestClient):
    resp = client.get("/trace/view")
    assert resp.status_code == 422


def test_post_query_two_source_query_returns_provenance_tagged_evidence():
    """The Phase 4 exit criterion, now exercised through the actual HTTP
    API surface rather than calling the graph directly."""
    registry = build_registry(CONFIG_DIR)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=VAULT_DIR)
    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    ef = HashingEmbeddingFunction()
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name="api_test_two_source", embedding_function=ef)
    chroma = ChromaConnector(
        manifest=manifests["chroma"], client=chroma_client, collection_name="api_test_two_source", embedding_function=ef
    )
    web = FakeWebConnector(manifests["web_search"])
    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)

    analyzer_client = FakeLLMClient(
        _requirements_json(
            paradigm_hint="keyword",
            privacy_sensitivity="confidential",
            expects_personal_knowledge=True,
        )
    )
    synthesis_client = FakeLLMClient("Standing desks helped with back pain [1][2].")

    app = create_app(registry, analyzer_client, synthesis_client)
    local_client = TestClient(app)

    resp = local_client.post(
        "/query", json={"query": "advice on my divorce settlement", "top_k": 3}
    )
    data = resp.json()

    selected = {step["connector_id"] for step in data["plan_trace"]["execution_plan"]["steps"]}
    assert selected == {"obsidian", "chroma"}

    sources_in_evidence = {ev["source_id"] for ev in data["evidence"]}
    assert sources_in_evidence == {"obsidian", "chroma"}
    assert "web_search" not in sources_in_evidence