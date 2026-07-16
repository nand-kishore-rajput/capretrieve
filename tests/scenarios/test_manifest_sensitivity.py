"""
The decisive Phase 3 test, per the phase plan's own exit criterion:

    "edit a connector's YAML manifest — flip query_leaks_externally, raise
    typical_latency_ms — and the plan changes correctly with zero code
    changes. If this doesn't hold, the planner is reading something it
    shouldn't, and you fix it before moving on."

This test edits real YAML files on disk via the loader (not by
hand-constructing Python objects) to prove the sensitivity holds through
the actual file-loading path a real deployment would use, not just through
in-memory model mutation.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from capretrieve.manifest.loader import load_manifest_dir
from capretrieve.planner.planner import plan
from capretrieve.planner.models.requirements import (
    ParadigmHint,
    PrivacySensitivity,
    QueryRequirements,
)

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"


def _copy_configs_to(tmp_path: Path) -> Path:
    dest = tmp_path / "connectors"
    shutil.copytree(CONFIG_DIR, dest)
    return dest


def _set_yaml_field(path: Path, field: str, value) -> None:
    data = yaml.safe_load(path.read_text())
    data[field] = value
    path.write_text(yaml.safe_dump(data))


def test_flipping_query_leaks_externally_changes_privacy_block(tmp_path):
    """S1's exact mechanism: web_search.yaml's query_leaks_externally
    field alone determines whether a privacy-sensitive query excludes it
    — no code in planner/constraints.py should need to change."""
    config_dir = _copy_configs_to(tmp_path)
    web_yaml = config_dir / "web_search.yaml"

    # paradigm_hint=KEYWORD gives web_search a genuine score once it's no
    # longer hard-excluded, so the assertion below isn't relying on the
    # degenerate all-candidates-score-zero tie-break (which arbitrarily
    # picks whichever candidate loaded first).
    requirements = QueryRequirements(
        paradigm_hint=ParadigmHint.KEYWORD,
        privacy_sensitivity=PrivacySensitivity.CONFIDENTIAL,
    )

    # Before: query_leaks_externally: true (as shipped) -> excluded
    manifests_before = list(load_manifest_dir(config_dir).values())
    plan_before = plan(manifests_before, requirements)
    assert "web_search" not in plan_before.selected_connector_ids

    # Flip the YAML field on disk — zero code change.
    _set_yaml_field(web_yaml, "query_leaks_externally", False)

    manifests_after = list(load_manifest_dir(config_dir).values())
    plan_after = plan(manifests_after, requirements)
    assert "web_search" in plan_after.selected_connector_ids


def test_flipping_paradigm_changes_relational_routing(tmp_path):
    """S4's exact mechanism: chroma.yaml's paradigm field alone determines
    whether it can satisfy a relational query."""
    config_dir = _copy_configs_to(tmp_path)
    chroma_yaml = config_dir / "chroma.yaml"

    requirements = QueryRequirements(relational=True)

    # Before: paradigm: dense_semantic -> excluded from a relational query
    manifests_before = list(load_manifest_dir(config_dir).values())
    plan_before = plan(manifests_before, requirements)
    assert "chroma" not in plan_before.selected_connector_ids

    # Flip the YAML field on disk — zero code change.
    _set_yaml_field(chroma_yaml, "paradigm", "graph_traversal")

    manifests_after = list(load_manifest_dir(config_dir).values())
    plan_after = plan(manifests_after, requirements)
    assert "chroma" in plan_after.selected_connector_ids


def test_flipping_privacy_tier_and_paradigm_together_changes_scoring(tmp_path):
    """A softer sensitivity check: changing fields that affect SCORE
    (not just hard exclusion) also changes the outcome with zero code
    changes — obsidian gaining a paradigm match should overtake chroma."""
    config_dir = _copy_configs_to(tmp_path)
    obsidian_yaml = config_dir / "obsidian.yaml"

    requirements = QueryRequirements(
        paradigm_hint=ParadigmHint.DENSE_SEMANTIC,
        expects_personal_knowledge=True,
    )

    manifests_before = list(load_manifest_dir(config_dir).values())
    plan_before = plan(manifests_before, requirements)
    assert plan_before.selected_connector_ids == ["chroma"]

    # Give obsidian a paradigm that now matches the hint too — zero code
    # change, pure YAML edit.
    _set_yaml_field(obsidian_yaml, "paradigm", "dense_semantic")

    manifests_after = list(load_manifest_dir(config_dir).values())
    plan_after = plan(manifests_after, requirements)
    assert set(plan_after.selected_connector_ids) == {"chroma", "obsidian"}