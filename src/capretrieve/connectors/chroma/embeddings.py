"""
Embedding functions for the Chroma connector.

Two implementations:

1. HashingEmbeddingFunction — deterministic, offline, dependency-free
   bag-of-words hashing. Used in tests and as the offline fallback.
   Good enough to distinguish topically different documents but fails
   on semantic similarity (e.g. "baseline comparison" doesn't match
   Baseline Comparison.md if the exact tokens don't appear). This was
   the original implementation and remains default for tests.

2. SentenceTransformerEmbeddingFunction — real semantic embeddings via
   sentence-transformers. Downloads a model on first use (~80MB for
   all-MiniLM-L6-v2). Dramatically better retrieval quality. Used in
   production via EMBEDDING_MODEL env var.

The active implementation is selected by get_embedding_function():
  - If EMBEDDING_MODEL is set: use SentenceTransformerEmbeddingFunction
  - Otherwise: use HashingEmbeddingFunction (safe default, no downloads)

The Connector interface never changes regardless of which is active.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import os
import re
from collections import Counter
from typing import Any


from chromadb.api.types import Documents, Embeddings, EmbeddingFunction

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _hash_token(token: str, dim: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % dim


class HashingEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Deterministic, offline embedding function. Kept for tests and
    offline environments. See module docstring for limitations.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    @staticmethod
    def name() -> str:
        return "capretrieve-hashing-embedding"

    def get_config(self) -> dict[str, Any]:
        return {"dim": self.dim}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "HashingEmbeddingFunction":
        return HashingEmbeddingFunction(dim=config.get("dim", 256))

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_one(text) for text in input]

    def embed_query(self, input: Documents) -> Embeddings:
        return self(input)

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        counts = Counter(_tokenize(text))
        for token, count in counts.items():
            vec[_hash_token(token, self.dim)] += count

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class SentenceTransformerEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Real semantic embeddings via sentence-transformers.

    Requires: pip install sentence-transformers
    Downloads the model on first use (cached in ~/.cache/huggingface).

    Recommended models (trade-off: quality vs size):
      - all-MiniLM-L6-v2       ~80MB,  384-dim, fast, good quality
      - all-mpnet-base-v2       ~420MB, 768-dim, better quality
      - BAAI/bge-small-en-v1.5  ~130MB, 384-dim, MTEB top performer (small)
      - BAAI/bge-base-en-v1.5   ~440MB, 768-dim, MTEB top performer (base)

    Set via EMBEDDING_MODEL env var, e.g.:
      EMBEDDING_MODEL=all-MiniLM-L6-v2
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        # Lazy import so the class can be defined without the package
        # installed — tests that use HashingEmbeddingFunction never
        # trigger this import.
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for SentenceTransformerEmbeddingFunction. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    @staticmethod
    def name() -> str:
        return "capretrieve-sentence-transformer"

    def get_config(self) -> dict[str, Any]:
        return {"model_name": self.model_name}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "SentenceTransformerEmbeddingFunction":
        return SentenceTransformerEmbeddingFunction(
            model_name=config.get("model_name", "all-MiniLM-L6-v2")
        )

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self._model.encode(
            list(input),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, input: Documents) -> Embeddings:
        return self(input)


def get_embedding_function() -> EmbeddingFunction:
    """
    Factory: returns the appropriate embedding function based on env vars.

    If EMBEDDING_MODEL is set, returns SentenceTransformerEmbeddingFunction
    with that model. Otherwise returns HashingEmbeddingFunction.

    The env var is read on every call; the instance is cached per model
    name, so the sentence-transformer model loads once per process.

    Leave EMBEDDING_MODEL unset (or empty) for offline/test mode.
    """
    model_name = os.environ.get("EMBEDDING_MODEL", "").strip()
    return _load_embedding_function(model_name)


@lru_cache(maxsize=4)
def _load_embedding_function(model_name: str) -> EmbeddingFunction:
    if model_name:
        return SentenceTransformerEmbeddingFunction(model_name)
    return HashingEmbeddingFunction()