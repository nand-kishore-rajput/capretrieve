"""
A lightweight, dependency-free embedding function for the Chroma connector.

ChromaDB's built-in default embedding function downloads an ONNX model on
first use, which makes ingestion non-reproducible offline and introduces a
network dependency this project doesn't otherwise have. For a project
whose subject is routing decisions rather than embedding quality, that
tradeoff isn't worth it.

HashingEmbeddingFunction is a simple bag-of-words hashing vectorizer:
deterministic, fully offline, and good enough to distinguish topically
different documents for demo/test purposes. Swap in a real
sentence-transformer or an API-based embedding model for
production-quality semantic search — the Connector interface (and every
consumer of it) doesn't change either way.
"""

from __future__ import annotations

import hashlib
import math
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
    Deterministic, offline embedding function: hashes tokens into a
    fixed-dimensional bag-of-words vector, L2-normalized so that a dot
    product between two vectors behaves like cosine similarity.

    Inherits chromadb's EmbeddingFunction base (rather than pure duck
    typing) and implements name()/get_config()/build_from_config() so
    chromadb treats it as a well-formed, non-legacy embedding function.
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
        """chromadb calls this specifically on the query path. Delegates
        to __call__ since this embedding function doesn't distinguish
        query vs. document embeddings."""
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