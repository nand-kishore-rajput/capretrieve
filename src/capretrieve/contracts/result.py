"""
Evidence / RetrievalResult — what every connector's retrieve() returns.

This is the common currency fusion/ dedups and normalizes across paradigms:
a Chroma cosine similarity and a web search rank both arrive as
Evidence.score, tagged with source_id so provenance survives into the
final synthesized answer.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Evidence(BaseModel):
    source_id: str
    """connector_id of the connector that produced this evidence."""

    content: str

    score: float
    """Raw, connector-native relevance score. NOT comparable across
    connectors until fusion/normalize.py has processed it (a cosine
    similarity and a search-engine rank use different scales)."""

    uri: str | None = None
    """Locator for the underlying item (file path, URL, note ID, etc.),
    used for provenance in the synthesized answer."""

    retrieved_at: datetime


class RetrievalResult(BaseModel):
    evidence: list[Evidence]