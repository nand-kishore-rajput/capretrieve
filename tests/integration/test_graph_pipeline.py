"""
Integration test for the full pipeline: analyze -> plan -> fan_out
(retrieve) -> fuse -> synthesize, wired together via graph/build.py.

Uses REAL Obsidian and Chroma connectors against the real fixture data
(same as tests/connectors/test_contract_conformance.py), plus a fake web
connector and fake LLM clients for the analyzer and synthesis steps —
external network calls (Tavily, OpenRouter) aren't available in this
environment, but the entire graph orchestration, planner routing, fan-out
parallelism, and fusion logic run for real.

Nothing here hard-codes fixture note names or counts: where an assertion
needs a concrete seed or neighbourhood, it is derived from the fixture
vault at test time, so the vault can be replaced without editing tests.

This directly covers Phase 4's exit criterion: "a query needing two
sources returns one fused, provenance-tagged answer."
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
import pytest

from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.connectors.obsidian.connector import ObsidianConnector
from capretrieve.connectors.obsidian.traversal import expand_neighbourhood
from capretrieve.connectors.obsidian.vault import load_vault
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.generation.synthesize import NO_EVIDENCE_ANSWER
from capretrieve.graph.build import build_graph
from capretrieve.manifest.models import CapabilityManifest
from capretrieve.registry.static import Registry, build_registry

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"
VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"
CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"

# Must match the depth graph/nodes/retrieve.py::_build_retrieval_filters uses.
TRAVERSAL_DEPTH = 1
RELATIONAL_TOP_K = 5


class FakeLLMClient:
    """Returns a fixed response every call, regardless of prompt content."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls.append(list(messages))
        return self.response


class FakeWebConnector:
    """Stand-in for the real Tavily-backed connector — real network calls
    aren't available in this test environment (see test_web_connector.py)."""

    def __init__(self, manifest: CapabilityManifest, evidence: list[Evidence] | None = None) -> None:
        self._manifest = manifest
        self._evidence = evidence if evidence is not None else []

    def manifest(self) -> CapabilityManifest:
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


def _pick_traversal_seed() -> tuple[str, set[str]]:
    """Choose a note from the fixture vault whose depth-1 neighbourhood is
    non-trivial (has at least one neighbour), strictly smaller than the
    whole vault (so keyword fallback is distinguishable), and fits within
    RELATIONAL_TOP_K (so a top_k cap can't truncate it)."""
    notes = load_vault(VAULT_DIR)
    for name in sorted(notes):
        hood = {n.note_name for n in expand_neighbourhood(notes, name, depth=TRAVERSAL_DEPTH)}
        if 1 < len(hood) <= RELATIONAL_TOP_K and len(hood) < len(notes):
            return name, hood
    pytest.fail(
        f"fixture vault {VAULT_DIR} has no note with a small, non-trivial "
        f"depth-{TRAVERSAL_DEPTH} neighbourhood; the seed_entity regression "
        "test needs one"
    )


@pytest.fixture
def wired_registry() -> Registry:
    registry = build_registry(CONFIG_DIR)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=VAULT_DIR)

    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    ef = HashingEmbeddingFunction()
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name="graph_integration_test",
                  embedding_function=ef)
    chroma = ChromaConnector(
        manifest=manifests["chroma"], client=chroma_client,
        collection_name="graph_integration_test", embedding_function=ef
    )

    web = FakeWebConnector(manifests["web_search"])

    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)
    return registry


async def test_single_source_query_selects_only_chroma(wired_registry):
    """S5-style: pure semantic query with no personal knowledge flag should
    route to chroma alone, not over-select. Note: expects_personal_knowledge
    must be False here — if True, the force-include policy correctly selects
    both local connectors, which is the right behaviour for 'my notes'
    queries and is tested separately."""
    analyzer_client = FakeLLMClient(
        _requirements_json(paradigm_hint="dense_semantic", expects_personal_knowledge=False)
    )
    synthesis_client = FakeLLMClient("Retrieval-augmented generation grounds answers [1].")

    graph = build_graph(wired_registry, analyzer_client, synthesis_client)
    result = await graph.ainvoke(
        {"query": "What does the literature say about retrieval-augmented generation?",
         "top_k": 3}
    )

    assert result["execution_plan"].selected_connector_ids == ["chroma"]
    assert len(result["raw_evidence"]) > 0
    assert all(ev.source_id == "chroma" for ev in result["raw_evidence"])


async def test_two_source_query_returns_one_fused_provenance_tagged_answer(
    wired_registry,
):
    """The Phase 4 exit criterion, verbatim: a query needing two sources
    returns one fused, provenance-tagged answer."""
    analyzer_client = FakeLLMClient(
        _requirements_json(
            paradigm_hint="keyword",
            privacy_sensitivity="confidential",
            expects_personal_knowledge=True,
        )
    )
    answer = "Your notes and the reference docs both cover this [1][2]."
    synthesis_client = FakeLLMClient(answer)

    graph = build_graph(wired_registry, analyzer_client, synthesis_client)
    # Query needs terms that appear in the vault, or Obsidian keyword
    # search returns nothing and the "both sources" assertion can't hold.
    result = await graph.ainvoke(
        {"query": "my notes on large language models and retrieval", "top_k": 3}
    )

    # two sources selected, web hard-blocked by privacy
    assert set(result["execution_plan"].selected_connector_ids) == {"obsidian", "chroma"}

    # both sources actually got queried in parallel
    sources_in_raw = {ev.source_id for ev in result["raw_evidence"]}
    assert sources_in_raw == {"obsidian", "chroma"}

    # fusion produced ONE combined, ranked list with provenance preserved
    fused = result["fused_evidence"]
    assert len(fused) > 0
    assert {ev.source_id for ev in fused} == {"obsidian", "chroma"}
    for ev in fused:
        assert ev.uri is not None  # provenance survived fusion

    # ONE final synthesized answer
    assert result["answer"] == answer


async def test_relational_query_selects_only_obsidian(wired_registry):
    """S4-style: relational query hard-excludes non-graph-traversal
    connectors."""
    analyzer_client = FakeLLMClient(
        _requirements_json(
            paradigm_hint="graph_traversal", relational=True, expects_personal_knowledge=True
        )
    )
    synthesis_client = FakeLLMClient("These notes link to it [1].")

    graph = build_graph(wired_registry, analyzer_client, synthesis_client)
    result = await graph.ainvoke(
        {"query": "What other notes link to my note on transformers?", "top_k": 5}
    )

    assert result["execution_plan"].selected_connector_ids == ["obsidian"]
    assert all(ev.source_id == "obsidian" for ev in result["raw_evidence"])


async def test_relational_query_with_seed_entity_actually_uses_graph_traversal(
    wired_registry,
):
    """Regression test: selecting the obsidian connector for a relational
    query is NOT enough to prove graph traversal actually ran — an
    earlier real end-to-end test (against the live OpenRouter API) showed
    the connector silently falling back to keyword search across the
    entire vault, because nothing in the pipeline populated
    QueryRequirements.seed_entity even though the connector was selected
    correctly.

    This test asserts on the EVIDENCE SHAPE, which is what distinguishes
    the two retrieval modes structurally:
      - graph traversal returns exactly the seed note + its direct
        wikilink/backlink neighbours, each scored 1.0
      - keyword search returns whatever the query's terms happen to
        match, scored by hit count, typically across more of the vault

    The seed and its expected neighbourhood are derived from the fixture
    vault (see _pick_traversal_seed). This test checks WIRING — that
    seed_entity reaches the connector and triggers traversal. Traversal
    correctness itself is covered exactly in tests/connectors/
    test_obsidian_traversal.py against a known sample graph.
    """
    seed, expected_hood = _pick_traversal_seed()
    all_notes = set(load_vault(VAULT_DIR))

    analyzer_client = FakeLLMClient(
        _requirements_json(
            paradigm_hint="graph_traversal",
            relational=True,
            expects_personal_knowledge=True,
            # lower-cased on purpose: exercises _resolve_seed_note end to end
            seed_entity=seed.lower(),
        )
    )
    synthesis_client = FakeLLMClient("These notes link to it [1][2].")

    graph = build_graph(wired_registry, analyzer_client, synthesis_client)
    result = await graph.ainvoke(
        {"query": f"What other notes link to my {seed.lower()} note?",
         "top_k": RELATIONAL_TOP_K}
    )

    evidence_uris = {Path(ev.uri).stem for ev in result["raw_evidence"]}

    # exactly the seed + its direct neighbours — nothing outside it
    assert evidence_uris == expected_hood
    assert evidence_uris != all_notes

    # graph traversal scores every result 1.0 uniformly; a varied score
    # distribution (as keyword search produces) would indicate the
    # seed_entity filter never reached the connector
    assert all(ev.score == 1.0 for ev in result["raw_evidence"])


async def test_empty_plan_skips_retrieval_and_still_synthesizes(wired_registry):
    """If the planner selects nothing, the graph should still complete
    (fuse over empty evidence, synthesize an honest 'no evidence' answer)
    rather than erroring.

    To force a genuinely empty plan, this constructs a registry whose
    MANIFEST set (not just its registered connectors) excludes obsidian —
    the planner only ever sees registry.manifests(), so a relational
    query then has no graph_traversal candidate to select at all.
    """
    all_manifests = wired_registry.manifests()
    non_relational_manifests = {
        cid: m for cid, m in all_manifests.items() if cid != "obsidian"
    }
    empty_only_registry = Registry(non_relational_manifests)

    chroma_client = chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )
    ef = HashingEmbeddingFunction()
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name="empty_plan_test",
                  embedding_function=ef)
    chroma = ChromaConnector(
        manifest=all_manifests["chroma"], client=chroma_client,
        collection_name="empty_plan_test", embedding_function=ef
    )
    web = FakeWebConnector(all_manifests["web_search"])
    empty_only_registry.register(chroma)
    empty_only_registry.register(web)

    analyzer_client = FakeLLMClient(_requirements_json(relational=True))
    synthesis_client = FakeLLMClient("I don't have a source that can answer this.")

    graph = build_graph(empty_only_registry, analyzer_client, synthesis_client)
    result = await graph.ainvoke({"query": "what links to X", "top_k": 3})

    assert result["execution_plan"].is_empty
    assert result.get("raw_evidence", []) == []
    assert result["fused_evidence"] == []
    assert result["answer"] == NO_EVIDENCE_ANSWER