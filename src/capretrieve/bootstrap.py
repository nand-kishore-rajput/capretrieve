"""
bootstrap.py — builds the REAL registry (real connectors) and REAL graph
(real OpenRouterClient for analyzer + synthesis, real Tavily-backed
WebSearchConnector) from Settings.

Not part of the original repo plan's file list — added because api/app.py
needs something that assembles real dependencies from configuration at
startup, and inlining this logic directly in app.py would make it
impossible to unit-test the wiring separately from the HTTP layer. Same
spirit as registry/errors.py: a small, deliberate addition.

This is also the first place in the whole project where the three
external calls that could only be tested against fakes during
development (Tavily search, OpenRouter analyzer, OpenRouter synthesis)
get wired up for real. Nothing here has been exercised against live APIs
in the sandbox this project was built in — see individual connector/LLM
client docstrings for the same caveat.
"""

from __future__ import annotations

import chromadb

from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.connectors.obsidian.connector import ObsidianConnector
from capretrieve.connectors.web.connector import WebSearchConnector
from capretrieve.graph.build import build_graph
from capretrieve.llm.client import OpenRouterClient
from capretrieve.registry.static import Registry, build_registry
from capretrieve.settings import Settings, get_settings


def build_default_registry(
    settings: Settings, chroma_client: chromadb.ClientAPI | None = None
) -> Registry:
    """
    Load manifests from settings.config_dir and register the three real
    connectors against real data:
      - obsidian: real vault at settings.vault_dir
      - chroma: ingested from settings.corpus_dir, using chroma_client if
        given, otherwise a real PersistentClient at
        settings.chroma_persist_dir
      - web_search: real Tavily client via settings.web_search_api_key
        (or keyless mode if unset — see WebSearchConnector's docstring)

    chroma_client is injectable for the same reason it is everywhere else
    in this project (see connectors/chroma/ingest.py's docstring):
    ChromaDB's PersistentClient does process-wide caching and background
    threading keyed by path, and constructing many of them in one process
    (e.g. once per test) is a documented source of hangs. Tests should
    inject a chromadb.EphemeralClient(); real usage (build_default_app)
    leaves this as None and gets the real on-disk client.
    """
    registry = build_registry(settings.config_dir)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=settings.vault_dir)

    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_dir),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
    ingest_corpus(settings.corpus_dir, client=chroma_client)
    chroma = ChromaConnector(manifest=manifests["chroma"], client=chroma_client)

    web = WebSearchConnector(
        manifest=manifests["web_search"], api_key=settings.web_search_api_key
    )

    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)
    return registry


def build_default_graph(settings: Settings, registry: Registry | None = None):
    """
    Build the full pipeline graph wired to real LLM clients. Raises if
    OPENROUTER_API_KEY isn't set — there's no meaningful keyless fallback
    for the analyzer/synthesis steps the way there is for Tavily search.
    """
    api_key = settings.require_openrouter_api_key()

    if registry is None:
        registry = build_default_registry(settings)

    analyzer_client = OpenRouterClient(api_key=api_key, model=settings.analyzer_model)
    synthesis_client = OpenRouterClient(api_key=api_key, model=settings.synthesis_model)

    return build_graph(
        registry,
        analyzer_client,
        synthesis_client,
        default_top_k=settings.default_top_k,
        max_fused_items=settings.max_fused_items,
    )


def build_default_app(settings: Settings | None = None):
    """
    The single top-level entrypoint for real deployment: real registry,
    real connectors, real OpenRouterClients, wired into the same
    create_app() factory used in tests (with fakes). This is what
    api/main.py calls for `uvicorn capretrieve.api.main:app`.
    """
    from capretrieve.api.app import create_app

    if settings is None:
        settings = get_settings()

    api_key = settings.require_openrouter_api_key()
    registry = build_default_registry(settings)
    analyzer_client = OpenRouterClient(api_key=api_key, model=settings.analyzer_model)
    synthesis_client = OpenRouterClient(api_key=api_key, model=settings.synthesis_model)

    return create_app(
        registry,
        analyzer_client,
        synthesis_client,
        default_top_k=settings.default_top_k,
    )