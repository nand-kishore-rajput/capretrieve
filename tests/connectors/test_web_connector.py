"""
Tests for connectors/web/connector.py — the Connector protocol
implementation over the Tavily search API.

Uses FakeTavilyClient (tests/connectors/fakes.py; duck-typed, only needs
.search()) rather than the real TavilyClient. Reasons: unit tests
shouldn't spend real API credits on every run, and the real Tavily
endpoint may not be reachable from every CI/sandbox network. The real SDK
is exercised structurally (constructor signature, keyless-mode
construction) in test_connector_constructs_real_tavily_client_when_no_client_injected;
an actual live search call is NOT covered here and should be smoke-tested
manually with a real WEB_SEARCH_API_KEY before relying on this connector
in a demo.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
from tavily import TavilyClient

from capretrieve.connectors.web.connector import WebSearchConnector
from capretrieve.contracts.health import HealthState
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.manifest.loader import load_manifest_file
from tests.connectors.fakes import SAMPLE_TAVILY_RESPONSE as SAMPLE_RESPONSE
from tests.connectors.fakes import FakeTavilyClient

MANIFEST_PATH = Path(__file__).parents[2] / "configs" / "connectors" / "web_search.yaml"


@pytest.fixture
def manifest():
    return load_manifest_file(MANIFEST_PATH)


def test_manifest_matches_loaded_yaml(manifest):
    fake = FakeTavilyClient()
    connector = WebSearchConnector(manifest=manifest, client=fake)
    assert connector.manifest() == manifest
    assert connector.manifest().connector_id == "web_search"
    assert connector.manifest().query_leaks_externally is True


async def test_health_ok_with_injected_client(manifest):
    fake = FakeTavilyClient()
    connector = WebSearchConnector(manifest=manifest, client=fake)
    health = await connector.health()
    assert health.state == HealthState.OK


async def test_health_ok_with_api_key(manifest):
    connector = WebSearchConnector(manifest=manifest, api_key="tvly-fake-key-for-testing")
    health = await connector.health()
    assert health.state == HealthState.OK


async def test_health_degraded_with_no_configuration(manifest):
    connector = WebSearchConnector(manifest=manifest)  # no api_key, no client
    health = await connector.health()
    assert health.state == HealthState.DEGRADED
    assert "keyless" in health.detail.lower()


async def test_retrieve_maps_results_to_evidence(manifest):
    fake = FakeTavilyClient(response=SAMPLE_RESPONSE)
    connector = WebSearchConnector(manifest=manifest, client=fake)

    result = await connector.retrieve(
        RetrievalRequest(query="standing desk back pain research", top_k=5)
    )

    assert len(result.evidence) == 2
    top = result.evidence[0]
    assert top.source_id == "web_search"
    assert top.uri == "https://example.com/standing-desks"
    assert top.score == pytest.approx(0.91)
    assert "back pain" in top.content


async def test_retrieve_passes_query_and_top_k_through(manifest):
    fake = FakeTavilyClient(response=SAMPLE_RESPONSE)
    connector = WebSearchConnector(manifest=manifest, client=fake)

    await connector.retrieve(RetrievalRequest(query="some query", top_k=3))

    assert fake.last_query == "some query"
    assert fake.last_kwargs["max_results"] == 3


async def test_retrieve_converts_deadline_ms_to_seconds(manifest):
    fake = FakeTavilyClient(response=SAMPLE_RESPONSE)
    connector = WebSearchConnector(manifest=manifest, client=fake)

    await connector.retrieve(
        RetrievalRequest(query="some query", top_k=3, deadline_ms=2500)
    )

    assert fake.last_kwargs["timeout"] == pytest.approx(2.5)


async def test_retrieve_deadline_floor_is_one_second(manifest):
    fake = FakeTavilyClient(response=SAMPLE_RESPONSE)
    connector = WebSearchConnector(manifest=manifest, client=fake)

    await connector.retrieve(
        RetrievalRequest(query="some query", top_k=3, deadline_ms=100)
    )

    assert fake.last_kwargs["timeout"] == pytest.approx(1.0)


async def test_retrieve_no_deadline_omits_timeout_kwarg(manifest):
    fake = FakeTavilyClient(response=SAMPLE_RESPONSE)
    connector = WebSearchConnector(manifest=manifest, client=fake)

    await connector.retrieve(RetrievalRequest(query="some query", top_k=3))

    assert "timeout" not in fake.last_kwargs


async def test_retrieve_empty_results_returns_no_evidence(manifest):
    fake = FakeTavilyClient(response={"results": []})
    connector = WebSearchConnector(manifest=manifest, client=fake)

    result = await connector.retrieve(RetrievalRequest(query="no matches", top_k=5))
    assert result.evidence == []


async def test_retrieve_respects_top_k_even_if_api_returns_more(manifest):
    fake = FakeTavilyClient(response=SAMPLE_RESPONSE)  # 2 results
    connector = WebSearchConnector(manifest=manifest, client=fake)

    result = await connector.retrieve(RetrievalRequest(query="anything", top_k=1))
    assert len(result.evidence) == 1


def test_connector_constructs_real_tavily_client_when_no_client_injected(manifest):
    """Structural check only — confirms WebSearchConnector wires up a real
    tavily.TavilyClient (in keyless mode, no network call) when no client
    is injected. Does not perform a live search."""
    connector = WebSearchConnector(manifest=manifest, api_key=None)
    assert isinstance(connector._client, TavilyClient)

class SlowTavilyClient(FakeTavilyClient):
    def search(self, query: str, **kwargs) -> dict:
        time.sleep(0.3)  # the real TavilyClient.search is a blocking call
        return super().search(query, **kwargs)


@pytest.mark.asyncio
async def test_retrieve_does_not_block_the_event_loop(manifest):
    connector = WebSearchConnector(manifest=manifest, client=SlowTavilyClient(SAMPLE_RESPONSE))
    req = RetrievalRequest(query="q", top_k=2)

    start = time.perf_counter()
    await asyncio.gather(connector.retrieve(req), connector.retrieve(req))

    assert time.perf_counter() - start < 0.5
