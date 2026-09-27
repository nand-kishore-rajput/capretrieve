"""
Tests for connectors/obsidian/connector.py — the Connector protocol
implementation wrapping vault.py + traversal.py.

Retrieval tests run against `sample_vault` (tests/connectors/conftest.py);
health is also checked against the real fixture vault.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capretrieve.connectors.obsidian.connector import ObsidianConnector, _resolve_seed_note
from capretrieve.contracts.health import HealthState
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.manifest.loader import load_manifest_file

FIXTURE_VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"
MANIFEST_PATH = Path(__file__).parents[2] / "configs" / "connectors" / "obsidian.yaml"

RETRO_NEIGHBOURHOOD = {"Project Retrospective", "Sprint Planning", "Standing Desk"}


@pytest.fixture
def connector(sample_vault: Path) -> ObsidianConnector:
    manifest = load_manifest_file(MANIFEST_PATH)
    return ObsidianConnector(manifest=manifest, vault_dir=sample_vault)


def _traversal_request(seed: str, depth: int = 1) -> RetrievalRequest:
    return RetrievalRequest(
        query="ignored in traversal mode",
        top_k=10,
        filters={"seed_note": seed, "depth": depth},
    )


def test_manifest_matches_loaded_yaml(connector: ObsidianConnector):
    manifest = load_manifest_file(MANIFEST_PATH)
    assert connector.manifest() == manifest
    assert connector.manifest().connector_id == "obsidian"


@pytest.mark.asyncio
async def test_health_ok_for_sample_vault(connector: ObsidianConnector):
    health = await connector.health()
    assert health.state == HealthState.OK


@pytest.mark.asyncio
async def test_health_ok_for_fixture_vault():
    manifest = load_manifest_file(MANIFEST_PATH)
    real = ObsidianConnector(manifest=manifest, vault_dir=FIXTURE_VAULT_DIR)
    health = await real.health()
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
    result = await connector.retrieve(_traversal_request("Project Retrospective"))
    uris = {Path(ev.uri).stem for ev in result.evidence}
    assert uris == RETRO_NEIGHBOURHOOD
    assert all(ev.source_id == "obsidian" for ev in result.evidence)


@pytest.mark.asyncio
async def test_retrieve_graph_traversal_unknown_seed_returns_empty(
    connector: ObsidianConnector,
):
    result = await connector.retrieve(
        RetrievalRequest(query="ignored", top_k=10, filters={"seed_note": "Does Not Exist"})
    )
    assert result.evidence == []


@pytest.mark.asyncio
async def test_retrieve_graph_traversal_matches_seed_case_insensitively(
    connector: ObsidianConnector,
):
    """Regression test: an LLM-extracted seed_entity won't match the
    vault's exact note-name casing (e.g. "project retrospective" vs.
    "Project Retrospective"). This must still trigger graph traversal,
    not silently fall through to keyword search over the whole vault."""
    result = await connector.retrieve(_traversal_request("project retrospective"))
    uris = {Path(ev.uri).stem for ev in result.evidence}
    assert uris == RETRO_NEIGHBOURHOOD


@pytest.mark.asyncio
async def test_retrieve_graph_traversal_matches_seed_with_extra_words(
    connector: ObsidianConnector,
):
    """An LLM might extract a slightly padded phrase (e.g. including "my")
    rather than the bare note title — substring matching should still
    resolve it correctly."""
    result = await connector.retrieve(_traversal_request("my project retrospective"))
    uris = {Path(ev.uri).stem for ev in result.evidence}
    assert "Project Retrospective" in uris


@pytest.mark.asyncio
async def test_retrieve_graph_traversal_does_not_return_all_vault_notes(
    connector: ObsidianConnector,
):
    """The exact real-world regression: graph traversal from a seed with
    only 3 connected notes must NOT return all 4 notes in the vault (that
    would mean it silently fell back to keyword search)."""
    result = await connector.retrieve(_traversal_request("project retrospective"))
    uris = {Path(ev.uri).stem for ev in result.evidence}
    assert "Intermittent Fasting" not in uris
    assert len(uris) == 3
    assert all(ev.score == 1.0 for ev in result.evidence)


class TestResolveSeedNote:
    """Direct tests for the _resolve_seed_note helper, isolated from the
    full retrieve() flow."""

    def test_exact_match(self):
        notes = {"Project Retrospective": object()}
        assert _resolve_seed_note(notes, "Project Retrospective") == "Project Retrospective"

    def test_case_insensitive_match(self):
        notes = {"Project Retrospective": object()}
        assert _resolve_seed_note(notes, "project retrospective") == "Project Retrospective"

    def test_substring_match_seed_contains_note_name(self):
        notes = {"Project Retrospective": object()}
        assert _resolve_seed_note(notes, "my project retrospective") == "Project Retrospective"

    def test_substring_match_note_name_contains_seed(self):
        notes = {"Q3 Planning Doc": object()}
        assert _resolve_seed_note(notes, "planning") == "Q3 Planning Doc"

    def test_no_match_returns_none(self):
        notes = {"Project Retrospective": object()}
        assert _resolve_seed_note(notes, "completely unrelated phrase xyz") is None

    def test_prefers_longest_candidate_when_multiple_match(self):
        """Fixture deliberately avoids any note that's an EXACT match to
        the seed — "plan" is a substring of both note names below, but
        neither equals "plan" exactly, so this genuinely exercises the
        longest-candidate tie-break rather than short-circuiting on the
        earlier exact-match check."""
        notes = {"Plan A": object(), "Plan A Details": object()}
        assert _resolve_seed_note(notes, "plan") == "Plan A Details"

    def test_exact_match_wins_over_a_longer_substring_candidate(self):
        """An exact (case-insensitive) match should win even when a
        different, longer note name would also match as a substring —
        exact identity is a stronger signal than partial overlap with a
        differently-named note, regardless of which is longer."""
        notes = {"Planning": object(), "Q3 Planning Doc": object()}
        assert _resolve_seed_note(notes, "planning") == "Planning"