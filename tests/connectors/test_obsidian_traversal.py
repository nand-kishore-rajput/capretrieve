"""
Tests for connectors/obsidian/traversal.py: link-neighbourhood expansion
via wikilinks and backlinks. This is the logic S4 (relational/multi-hop)
depends on.

Runs against `sample_vault` (tests/connectors/conftest.py), whose graph
shape is documented there, so neighbourhood assertions are exact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capretrieve.connectors.obsidian.traversal import expand_neighbourhood
from capretrieve.connectors.obsidian.vault import load_vault


@pytest.fixture
def notes(sample_vault: Path):
    return load_vault(sample_vault)


def test_expand_depth_zero_returns_only_seed(notes):
    result = expand_neighbourhood(notes, "Project Retrospective", depth=0)
    assert {n.note_name for n in result} == {"Project Retrospective"}


def test_expand_depth_one_returns_direct_neighbours(notes):
    result = expand_neighbourhood(notes, "Project Retrospective", depth=1)
    names = {n.note_name for n in result}
    assert names == {"Project Retrospective", "Sprint Planning", "Standing Desk"}


def test_expand_follows_backlinks(notes):
    # Standing Desk has no outgoing links; its only neighbour is reachable
    # via the backlink from Project Retrospective (graph is undirected).
    result = expand_neighbourhood(notes, "Standing Desk", depth=1)
    assert {n.note_name for n in result} == {"Standing Desk", "Project Retrospective"}


def test_expand_depth_two_reaches_second_hop(notes):
    result = expand_neighbourhood(notes, "Standing Desk", depth=2)
    assert {n.note_name for n in result} == {
        "Standing Desk",
        "Project Retrospective",
        "Sprint Planning",
    }


def test_expand_unknown_seed_returns_empty(notes):
    result = expand_neighbourhood(notes, "Does Not Exist", depth=2)
    assert result == []


def test_expand_isolated_note_returns_only_itself(notes):
    # Intermittent Fasting has no wikilinks or backlinks in the sample vault
    result = expand_neighbourhood(notes, "Intermittent Fasting", depth=3)
    assert {n.note_name for n in result} == {"Intermittent Fasting"}


def test_expand_default_depth_is_one(notes):
    default = expand_neighbourhood(notes, "Project Retrospective")
    explicit = expand_neighbourhood(notes, "Project Retrospective", depth=1)
    assert {n.note_name for n in default} == {n.note_name for n in explicit}


def test_expand_stops_growing_once_frontier_exhausted(notes):
    """A deep depth shouldn't error or loop forever once the graph is
    fully explored — it should just stop growing."""
    depth_2 = expand_neighbourhood(notes, "Project Retrospective", depth=2)
    depth_10 = expand_neighbourhood(notes, "Project Retrospective", depth=10)
    assert {n.note_name for n in depth_2} == {n.note_name for n in depth_10}