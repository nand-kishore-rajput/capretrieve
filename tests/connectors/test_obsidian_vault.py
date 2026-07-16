"""
Tests for connectors/obsidian/vault.py: frontmatter parsing, tag
extraction (both frontmatter and inline #tags), and that ObsidianReader's
wikilink/backlink metadata survives into our Note model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capretrieve.connectors.obsidian.vault import (
    _extract_inline_tags,
    _normalize_frontmatter_tags,
    _parse_frontmatter,
    load_vault,
)

VAULT_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "vault"


# ---- unit-level parsing helpers -------------------------------------------


def test_parse_frontmatter_extracts_dict_and_body():
    raw = "---\ntags: [a, b]\ndate: 2025-01-01\n---\n\n# Title\nbody text\n"
    fm, body = _parse_frontmatter(raw)
    assert fm == {"tags": ["a", "b"], "date": __import__("datetime").date(2025, 1, 1)}
    assert "body text" in body
    assert "---" not in body


def test_parse_frontmatter_missing_block_returns_empty_dict():
    raw = "# Title\nno frontmatter here\n"
    fm, body = _parse_frontmatter(raw)
    assert fm == {}
    assert body == raw


def test_parse_frontmatter_malformed_yaml_is_treated_as_absent():
    raw = "---\ntags: [unclosed\n---\nbody\n"
    fm, body = _parse_frontmatter(raw)
    assert fm == {}
    assert body == raw


def test_parse_frontmatter_non_mapping_is_treated_as_absent():
    raw = "---\n- just\n- a\n- list\n---\nbody\n"
    fm, body = _parse_frontmatter(raw)
    assert fm == {}
    assert body == raw


def test_extract_inline_tags_finds_multiple_and_dedupes():
    text = "some text #health and more #health/exercise stuff #work"
    tags = _extract_inline_tags(text)
    assert tags == sorted({"health", "health/exercise", "work"})


def test_extract_inline_tags_ignores_bare_hash_in_headers_marker():
    # a markdown header "# Title" shouldn't be picked up as a tag since
    # there's no non-whitespace tag body directly after a lone '#'
    text = "# Title\nbody #realtag"
    tags = _extract_inline_tags(text)
    assert tags == ["realtag"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ({}, []),
        ({"tags": "solo"}, ["solo"]),
        ({"tags": ["a", "b"]}, ["a", "b"]),
        ({"tags": None}, []),
        ({"tags": 5}, []),
    ],
)
def test_normalize_frontmatter_tags(raw, expected):
    assert _normalize_frontmatter_tags(raw) == expected


# ---- load_vault against the real fixture vault -----------------------------


def test_load_vault_finds_all_fixture_notes():
    notes = load_vault(VAULT_DIR)
    assert set(notes.keys()) == {
        "Project Retrospective",
        "Sprint Planning",
        "Standing Desk",
        "Intermittent Fasting",
    }


def test_load_vault_parses_frontmatter_tags():
    notes = load_vault(VAULT_DIR)
    assert "work" in notes["Project Retrospective"].tags
    assert "retrospective" in notes["Project Retrospective"].tags


def test_load_vault_merges_inline_and_frontmatter_tags():
    notes = load_vault(VAULT_DIR)
    standing_desk = notes["Standing Desk"]
    # frontmatter declares health+equipment; body also has an inline #health
    assert "health" in standing_desk.tags
    assert "equipment" in standing_desk.tags
    # dedup: 'health' appears in both places but only once in the result
    assert standing_desk.tags.count("health") == 1


def test_load_vault_wikilinks_and_backlinks():
    notes = load_vault(VAULT_DIR)
    retro = notes["Project Retrospective"]
    assert set(retro.wikilinks) == {"Standing Desk", "Sprint Planning"}
    assert "Sprint Planning" in retro.backlinks

    standing_desk = notes["Standing Desk"]
    assert "Project Retrospective" in standing_desk.backlinks
    assert standing_desk.wikilinks == []


def test_load_vault_content_excludes_frontmatter_block():
    notes = load_vault(VAULT_DIR)
    fasting = notes["Intermittent Fasting"]
    assert "---" not in fasting.content
    assert "tags:" not in fasting.content
    assert "16:8" in fasting.content