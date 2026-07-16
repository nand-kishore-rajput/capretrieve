"""
QueryRequirements — the structured, machine-readable output of the
requirement analyzer (planner/analyzer.py).

This is the other half of the contract that replaces prose-based routing:
CapabilityManifest declares what a source CAN do; QueryRequirements
declares what a QUERY NEEDS. The planner (constraints.py, scoring.py)
matches one against the other using only typed fields — never free text.

Architectural invariant: this module imports nothing but the standard
library. planner/models/ as a whole must import only manifest/ + stdlib
(enforced by tests/architecture/test_planner_models_pure.py) — it must
never import connectors/ or registry/, since QueryRequirements is
produced without any knowledge of which connectors exist.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Freshness(str, Enum):
    """How current the query needs its answer to be. Distinct from
    manifest.Freshness (that's what a connector CAN offer); this is what
    the query ASKS for."""

    ANY = "any"
    RECENT = "recent"
    LIVE = "live"


class PrivacySensitivity(str, Enum):
    """How sensitive the query's content is. Drives the hard privacy
    block in constraints.py against manifest.query_leaks_externally."""

    NONE = "none"
    PERSONAL = "personal"
    CONFIDENTIAL = "confidential"


class ParadigmHint(str, Enum):
    """The analyzer's best guess at which retrieval paradigm fits this
    query — used as a soft signal in scoring.py, not a hard requirement.
    UNKNOWN means the analyzer couldn't confidently tell."""

    DENSE_SEMANTIC = "dense_semantic"
    GRAPH_TRAVERSAL = "graph_traversal"
    KEYWORD = "keyword"
    UNKNOWN = "unknown"


class QueryRequirements(BaseModel):
    """
    Structured requirements extracted from a natural-language query by
    the LLM analyzer. This is the ONLY thing the planner sees from the
    analyzer — never the raw query text, never a connector name.
    """

    paradigm_hint: ParadigmHint = ParadigmHint.UNKNOWN

    relational: bool = False
    """True if the query requires following relationships between items
    (e.g. links between notes) rather than similarity/keyword recall.
    Drives S4-style routing to a graph_traversal connector."""

    needs_freshness: Freshness = Freshness.ANY

    privacy_sensitivity: PrivacySensitivity = PrivacySensitivity.NONE

    expects_personal_knowledge: bool = False
    """True if the query is about the person's own notes/history (e.g.
    "what did I conclude...") rather than general public knowledge."""

    seed_entity: str | None = None
    """The specific named entity the query wants to traverse relationships
    from — e.g. for "what other notes link to my project retrospective",
    this would be "project retrospective". Only meaningful when
    relational=True; None if the query doesn't name a specific starting
    point, or isn't relational at all.

    This is extracted purely from the query's own text (an ordinary
    entity-extraction task), not from any knowledge of what sources or
    connectors exist — it doesn't compromise the analyzer isolation
    invariant. A connector that supports seeded traversal (e.g. Obsidian)
    is expected to match this against its own item names case-insensitively,
    since the analyzer has no way to know the exact casing used in any
    particular vault/corpus."""