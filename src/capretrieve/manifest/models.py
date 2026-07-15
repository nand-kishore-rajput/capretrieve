"""
CapabilityManifest — the structured, machine-readable declaration of what a
connector can do.

This is the contract that replaces prose tool-descriptions. The planner
(planner/) reads ONLY the typed fields below to make routing decisions.
`scope` is the one exception: it is free-text documentation for humans and
must never be read by planner code (enforced by
tests/architecture/test_no_freetext_in_planner.py).

Every field here must be traceable to at least one fixture scenario in
fixtures/scenarios.yaml. If a field isn't driving a decision in some
scenario, it doesn't belong here yet — add it back when a scenario needs it
(see Phase 6: latency/cost budget fields return for S3).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Paradigm(str, Enum):
    """How the connector finds relevant content."""

    DENSE_SEMANTIC = "dense_semantic"
    GRAPH_TRAVERSAL = "graph_traversal"
    KEYWORD = "keyword"


class Freshness(str, Enum):
    """How current the connector's data is."""

    STATIC = "static"
    INDEX_TIME = "index_time"
    LIVE = "live"


class PrivacyTier(str, Enum):
    """Where the connector's data lives, relative to the user's control."""

    PRIVATE_LOCAL = "private_local"
    PUBLIC_EXTERNAL = "public_external"


class CapabilityManifest(BaseModel):
    """
    Declared capabilities for a single connector.

    Instances are constructed from configs/connectors/*.yaml by
    manifest/loader.py — never hand-built inside connector classes. Keeping
    manifests as data (not code) is what lets the schema evolve independently
    of connector implementations, and what makes the Phase 3 exit criterion
    possible: editing a YAML field changes planner behavior with zero code
    changes.
    """

    connector_id: str

    paradigm: Paradigm

    freshness: Freshness

    privacy_tier: PrivacyTier

    query_leaks_externally: bool = Field(
        ...,
        description=(
            "Whether invoking this connector sends the raw query text to a "
            "third party outside the user's control. Kept separate from "
            "privacy_tier because the two facts are independent: a private "
            "remote database (privacy_tier=private_local or a future "
            "private_remote tier) does not necessarily leak the query, and "
            "a public external source always does. Drives the S1 hard "
            "privacy block in planner/constraints.py."
        ),
    )

    scope: str = Field(
        ...,
        description=(
            "Free-text human-readable note about what this connector covers. "
            "Documentation only. MUST NOT be read by planner/ code — doing "
            "so reintroduces prose-based routing, which is the exact "
            "pattern this project replaces."
        ),
    )