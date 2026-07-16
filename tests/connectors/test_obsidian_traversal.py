"""
Tests for connectors/obsidian/traversal.py: link-neighbourhood expansion
via wikilinks and backlinks. This is the logic S4 (relational/multi-hop)
depends on.
"""

from __future__ import annotations

from pathlib import Path

from capretrieve.connectors.obsidian.traversal import expand_neighbourhood
from capretrieve.connectors.obsidian.vault import load_vault

VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"


def test_expand_depth_zero_returns_only_seed():
    notes = load_vault(VAULT_DIR)
    result = expand_neighbourhood(notes, "Project Retrospective", depth=0)
    assert {n.note_name for n in result} == {"Project Retrospective"}


def test_expand_depth_one_returns_direct_neighbours():
    notes = load_vault(VAULT_DIR)
    result = expand_neighbourhood(notes, "Project Retrospective", depth=1)
    names = {n.note_name for n in result}
    assert names == {"Project Retrospective", "Sprint Planning", "Standing Desk"}


def test_expand_unknown_seed_returns_empty():
    notes = load_vault(VAULT_DIR)
    result = expand_neighbourhood(notes, "Does Not Exist", depth=2)
    assert result == []


def test_expand_isolated_note_returns_only_itself():
    notes = load_vault(VAULT_DIR)
    # Intermittent Fasting has no wikilinks or backlinks in the fixture vault
    result = expand_neighbourhood(notes, "Intermittent Fasting", depth=3)
    assert {n.note_name for n in result} == {"Intermittent Fasting"}


def test_expand_default_depth_is_one():
    notes = load_vault(VAULT_DIR)
    default = expand_neighbourhood(notes, "Project Retrospective")
    explicit = expand_neighbourhood(notes, "Project Retrospective", depth=1)
    assert {n.note_name for n in default} == {n.note_name for n in explicit}


def test_expand_stops_growing_once_frontier_exhausted():
    """A deep depth shouldn't error or loop forever once the graph is
    fully explored — it should just stop growing."""
    notes = load_vault(VAULT_DIR)
    depth_2 = expand_neighbourhood(notes, "Project Retrospective", depth=2)
    depth_10 = expand_neighbourhood(notes, "Project Retrospective", depth=10)
    assert {n.note_name for n in depth_2} == {n.note_name for n in depth_10}