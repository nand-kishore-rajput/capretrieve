"""
bootstrap.py — builds the REAL registry (real connectors) and REAL graph
from Settings. Provider-agnostic: the LLM client uses whatever api_base
and api_key are configured in settings (OpenRouter, Groq, or any other
OpenAI-compatible endpoint).
"""

from __future__ import annotations

import chromadb

from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.connectors.obsidian.connector import ObsidianConnector
from capretrieve.connectors.web.connector import WebSearchConnector
from capretrieve.graph.build import build_graph
from capretrieve.llm.client import LLMClient
from capretrieve.registry.static import Registry, build_registry
from capretrieve.settings import Settings, get_settings


def build_default_registry(
    settings: Settings,
    chroma_client: chromadb.ClientAPI | None = None,
    embedding_function=None,
) -> Registry:
    """
    Load manifests and register the three real connectors.

    embedding_function is injectable for the same reason chroma_client is:
    tests should pass HashingEmbeddingFunction() explicitly so they never
    depend on the EMBEDDING_MODEL env var (which may be set by load_dotenv()
    reading .env at import time even when the test runner sets EMBEDDING_MODEL=
    in the shell). Real usage leaves this as None, getting get_embedding_function()
    which reads the env var at startup time when it's actually correct.
    """
    from capretrieve.connectors.chroma.embeddings import get_embedding_function

    registry = build_registry(settings.config_dir)
    manifests = registry.manifests()

    obsidian = ObsidianConnector(manifest=manifests["obsidian"], vault_dir=settings.vault_dir)

    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_dir),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )

    ef = embedding_function if embedding_function is not None else get_embedding_function()
    ingest_corpus(settings.corpus_dir, client=chroma_client, embedding_function=ef)
    chroma = ChromaConnector(manifest=manifests["chroma"], client=chroma_client,
                             embedding_function=ef)

    web = WebSearchConnector(
        manifest=manifests["web_search"], api_key=settings.web_search_api_key
    )

    registry.register(obsidian)
    registry.register(chroma)
    registry.register(web)
    return registry


def _make_llm_client(settings: Settings, model: str) -> LLMClient:
    api_key = settings.require_llm_api_key()
    return LLMClient(
        api_base=settings.llm_api_base,
        api_key=api_key,
        model=model,
        max_tokens=settings.llm_max_tokens,
    )


def build_default_graph(settings: Settings, registry: Registry | None = None):
    """Build the full pipeline graph wired to real LLM clients."""
    if registry is None:
        registry = build_default_registry(settings)

    analyzer_client = _make_llm_client(settings, settings.analyzer_model)
    synthesis_client = _make_llm_client(settings, settings.synthesis_model)

    return build_graph(
        registry,
        analyzer_client,
        synthesis_client,
        default_top_k=settings.default_top_k,
        max_fused_items=settings.max_fused_items,
    )


def build_default_app(settings: Settings | None = None):
    """
    The single top-level entrypoint for real deployment. Wires the real
    registry and real LLM clients into create_app(). Provider is
    determined entirely by settings (LLM_API_BASE + LLM_API_KEY in .env).
    """
    from capretrieve.api.app import create_app

    if settings is None:
        settings = get_settings()

    registry = build_default_registry(settings)
    analyzer_client = _make_llm_client(settings, settings.analyzer_model)
    synthesis_client = _make_llm_client(settings, settings.synthesis_model)

    return create_app(
        registry,
        analyzer_client,
        synthesis_client,
        default_top_k=settings.default_top_k,
    )