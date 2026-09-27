"""
Contract conformance test — the Phase 2 exit criterion: "one
contract-conformance test runs parametrised over registry.all()".

Wires all three real connectors (Obsidian, Chroma, Web) into an actual
Registry, the same way registry/static.py + application wiring will do in
later phases, and verifies every registered connector is interchangeable
through the Connector protocol: correct manifest, a working health()
call, and retrieve() returning valid Evidence for a smoke query.

The web connector uses an injected FakeTavilyClient rather than a real
API call — see test_web_connector.py's docstring for why (no real Tavily
key/network available in this test environment). This test still proves
the connector satisfies the Connector protocol and integrates with the
registry identically to the two local connectors; it does not prove the
real Tavily API integration works, which the person running this suite
should smoke-test separately with a real WEB_SEARCH_API_KEY.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
import pytest

from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.connectors.obsidian.connector import ObsidianConnector
from capretrieve.connectors.web.connector import WebSearchConnector
from capretrieve.contracts.health import HealthState
from capretrieve.contracts.protocol import Connector
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.registry.static import build_registry
from tests.connectors.fakes import SAMPLE_TAVILY_RESPONSE, FakeTavilyClient

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"
VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"
CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"

# A smoke query per connector_id, chosen to actually match fixture content
# so "returns Evidence for a smoke query" is a meaningful assertion rather
# than trivially true on an empty result.
SMOKE_QUERIES = {
    "obsidian": "RAG systems retrieval",
    "chroma": "transformer attention mechanism",
    "web_search": "RAG hallucination reduction",
}


@pytest.fixture
def wired_registry():
    """Build a Registry with all three real connectors registered,
    exactly as later application wiring will do."""
    registry = build_registry(CONFIG_DIR)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=VAULT_DIR)

    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    ef = HashingEmbeddingFunction()
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name="conformance_test",
                  embedding_function=ef)
    chroma = ChromaConnector(
        manifest=manifests["chroma"], client=chroma_client,
        collection_name="conformance_test", embedding_function=ef
    )

    fake_tavily = FakeTavilyClient(response=SAMPLE_TAVILY_RESPONSE)
    web = WebSearchConnector(manifest=manifests["web_search"], client=fake_tavily)

    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)
    return registry


def test_registry_has_all_three_connectors(wired_registry):
    ids = {c.manifest().connector_id for c in wired_registry.all()}
    assert ids == {"obsidian", "chroma", "web_search"}


@pytest.mark.parametrize("connector_id", ["obsidian", "chroma", "web_search"])
def test_connector_satisfies_protocol(wired_registry, connector_id):
    connector = wired_registry.get(connector_id)
    assert isinstance(connector, Connector)


@pytest.mark.parametrize("connector_id", ["obsidian", "chroma", "web_search"])
def test_connector_manifest_matches_registry(wired_registry, connector_id):
    connector = wired_registry.get(connector_id)
    assert connector.manifest() == wired_registry.manifests()[connector_id]
    assert connector.manifest().connector_id == connector_id


@pytest.mark.parametrize("connector_id", ["obsidian", "chroma", "web_search"])
async def test_connector_health_does_not_error(wired_registry, connector_id):
    connector = wired_registry.get(connector_id)
    health = await connector.health()
    assert health.state in {HealthState.OK, HealthState.DEGRADED, HealthState.DOWN}


@pytest.mark.parametrize("connector_id", ["obsidian", "chroma", "web_search"])
async def test_connector_retrieve_returns_evidence_for_smoke_query(
    wired_registry, connector_id
):
    connector = wired_registry.get(connector_id)
    query = SMOKE_QUERIES[connector_id]

    result = await connector.retrieve(RetrievalRequest(query=query, top_k=3))

    assert len(result.evidence) >= 1
    for ev in result.evidence:
        assert ev.source_id == connector_id
        assert isinstance(ev.content, str) and ev.content
        assert ev.retrieved_at is not None