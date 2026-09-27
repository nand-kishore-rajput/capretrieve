"""
Session-wide test configuration.

Runs before any test module is imported, so environment set here is in
place before capretrieve.settings reads .env.
"""

from __future__ import annotations

import os
import pytest

from capretrieve.connectors.chroma.embeddings import _load_embedding_function

# Tests must never load sentence-transformers. Forces
# get_embedding_function() to return HashingEmbeddingFunction regardless
# of EMBEDDING_MODEL in .env. load_dotenv() (override=False) will not
# overwrite a variable that is already set, even to an empty string.
os.environ["EMBEDDING_MODEL"] = ""

@pytest.fixture(autouse=True)
def _clear_embedding_cache():
    _load_embedding_function.cache_clear()
    yield
    _load_embedding_function.cache_clear()