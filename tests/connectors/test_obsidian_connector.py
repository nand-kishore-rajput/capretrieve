"""
Tests for connectors/obsidian/connector.py — the Connector protocol
implementation wrapping vault.py + traversal.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capretrieve.connectors.obsidian.connector import ObsidianConnector
from capretrieve.contracts.health import HealthState
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.manifest.loader import load_manifest_file

VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"
MANIFEST_PATH = Path(__file__).parents[2] / "configs" / "connectors" / "obsidian.yaml"


@pytest.fixture
def connector() -> ObsidianConnector:
    manifest = load_manifest_file(MANIFEST_PATH)
    return ObsidianConnector(manifest=manifest, vault_dir=VAULT_DIR)


def test_manifest_matches_loaded_yaml(connector: ObsidianConnector):
    manifest = load_manifest_file(MANIFEST_PATH)
    assert connector.manifest() == manifest
    assert connector.manifest().connector_id == "obsidian"


@pytest.mark.asyncio
async def test_health_ok_for_real_vault(connector: ObsidianConnector):
    health = await connector.health()
    assert health.state == HealthState.OK


@pytest.mark.asyncio
async def test_health_down_for_missing_vault():
    manifest = load_manifest_file(MANIFEST_PATH)
    bad_connector = ObsidianConnector(manifest=manifest, vault_dir=Path("/no/such/vault"))
    health = await bad_connector.health()
    assert health.state == HealthState.DOWN


@pytest.mark.asyncio
async def test_health_degraded_for_empty_vault(tmp_path):
    manifest = load_manifest_file(MANIFEST_PATH)
    empty_connector = ObsidianConnector(manifest=manifest, vault_dir=tmp_path)
    health = await empty_connector.health()
    assert health.state == HealthState.DEGRADED


@pytest.mark.asyncio
async def test_retrieve_keyword_search_returns_relevant_note(connector: ObsidianConnector):
    result = await connector.retrieve(
        RetrievalRequest(query="intermittent fasting energy", top_k=3)
    )
    assert len(result.evidence) >= 1
    top = result.evidence[0]
    assert "Intermittent Fasting" in top.uri
    assert top.source_id == "obsidian"
    assert top.score > 0


@pytest.mark.asyncio
async def test_retrieve_keyword_search_respects_top_k(connector: ObsidianConnector):
    result = await connector.retrieve(RetrievalRequest(query="the", top_k=1))
    assert len(result.evidence) <= 1


@pytest.mark.asyncio
async def test_retrieve_keyword_search_no_match_returns_empty(connector: ObsidianConnector):
    result = await connector.retrieve(
        RetrievalRequest(query="zzz_no_such_term_anywhere", top_k=5)
    )
    assert result.evidence == []


@pytest.mark.asyncio
async def test_retrieve_graph_traversal_via_seed_filter(connector: ObsidianConnector):
    result = await connector.retrieve(
        RetrievalRequest(
            query="ignored in traversal mode",
            top_k=10,
            filters={"seed_note": "Project Retrospective", "depth": 1},
        )
    )
    uris = {Path(ev.uri).stem for ev in result.evidence}
    assert uris == {"Project Retrospective", "Sprint Planning", "Standing Desk"}
    assert all(ev.source_id == "obsidian" for ev in result.evidence)


@pytest.mark.asyncio
async def test_retrieve_graph_traversal_unknown_seed_returns_empty(
    connector: ObsidianConnector,
):
    result = await connector.retrieve(
        RetrievalRequest(
            query="ignored",
            top_k=10,
            filters={"seed_note": "Does Not Exist"},
        )
    )
    assert result.evidence == []