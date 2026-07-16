"""
Tests for connectors/chroma/embeddings.py — the offline, dependency-free
embedding function used in place of chromadb's default (network-dependent)
ONNX model.
"""

from __future__ import annotations

import math

from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction


def test_embedding_is_deterministic():
    ef = HashingEmbeddingFunction()
    a = [vec.tolist() for vec in ef(["the quick brown fox"])]
    b = [vec.tolist() for vec in ef(["the quick brown fox"])]
    assert a == b


def test_embedding_dimension_matches_config():
    ef = HashingEmbeddingFunction(dim=64)
    vec = ef(["hello world"])[0]
    assert len(vec) == 64


def test_embedding_is_l2_normalized():
    ef = HashingEmbeddingFunction()
    vec = ef(["some reasonably long piece of text to embed"])[0]
    norm = math.sqrt(sum(v * v for v in vec))
    assert math.isclose(norm, 1.0, abs_tol=1e-6)


def test_empty_string_embeds_to_zero_vector():
    ef = HashingEmbeddingFunction()
    vec = ef([""])[0]
    assert all(v == 0.0 for v in vec)


def test_similar_texts_are_closer_than_dissimilar_texts():
    ef = HashingEmbeddingFunction()
    a, b, c = ef(
        [
            "standing desk back pain ergonomics",
            "desk ergonomics reduce back pain",
            "sprint planning exit criteria",
        ]
    )

    def dot(x, y):
        return sum(xi * yi for xi, yi in zip(x, y))

    sim_ab = dot(a, b)
    sim_ac = dot(a, c)
    assert sim_ab > sim_ac


def test_embed_query_delegates_to_call():
    ef = HashingEmbeddingFunction()
    via_embed_query = [vec.tolist() for vec in ef.embed_query(["some text"])]
    via_call = [vec.tolist() for vec in ef(["some text"])]
    assert via_embed_query == via_call


def test_name_is_stable_string():
    ef = HashingEmbeddingFunction()
    assert isinstance(ef.name(), str)
    assert ef.name() == ef.name()