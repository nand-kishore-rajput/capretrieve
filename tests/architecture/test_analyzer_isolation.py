"""
Architectural invariant: the requirement analyzer's prompt contains no
connector names.

This is "the single most important isolation in the system" per the
phase plan: if the analyzer's prompt ever mentions "Obsidian", "Chroma",
"web search", or any connector_id, the LLM could start reasoning about
which SOURCE to use rather than purely what the QUERY needs — quietly
reintroducing prose-based tool-picking.

This test loads the real connector_ids from configs/connectors/*.yaml
(rather than hardcoding a list) so it stays correct even as connectors
are added or renamed.
"""

from __future__ import annotations

from pathlib import Path

from capretrieve.manifest.loader import load_manifest_dir
from capretrieve.planner.analyzer import load_prompt_template

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"

# Human-readable names/aliases worth checking for even though they aren't
# literal connector_ids — catches an analyzer prompt that says "search
# the web" or "your Obsidian vault" instead of the literal manifest id.
KNOWN_ALIASES = {
    "obsidian": ["obsidian"],
    "chroma": ["chroma", "chromadb"],
    "web_search": ["web search", "tavily", "web_search"],
}


def test_prompt_contains_no_connector_ids():
    manifests = load_manifest_dir(CONFIG_DIR)
    prompt = load_prompt_template().lower()

    violations = [
        connector_id for connector_id in manifests if connector_id.lower() in prompt
    ]
    assert not violations, (
        f"Analyzer prompt mentions connector_id(s) {violations} — the "
        f"analyzer must never see which connectors exist. See this file's "
        f"module docstring."
    )


def test_prompt_contains_no_known_connector_aliases():
    prompt = load_prompt_template().lower()

    violations = []
    for connector_id, aliases in KNOWN_ALIASES.items():
        for alias in aliases:
            if alias in prompt:
                violations.append((connector_id, alias))

    assert not violations, (
        f"Analyzer prompt mentions connector alias(es): {violations}. "
        f"Even human-readable references to a specific source leak "
        f"routing information into the requirement extraction step."
    )