"""
Scenario tests — fixtures/scenarios.yaml validated against the real
planner pipeline (constraints -> scoring -> selection) using real
connector manifests from configs/connectors/.

Only "active" scenarios (S1, S4, S5) are run here; S2 and S3 are marked
"deferred" in the fixture (S2 needs Phase 5 composition, S3 needs Phase 6
latency/cost fields) and are explicitly skipped with a reference back to
the fixture's own deferred_to_phase field, not silently ignored.

QueryRequirements are hand-authored per scenario rather than produced by
a live LLM call — this file tests the PLANNER's routing logic against
ground truth, not the ANALYZER's ability to extract requirements from raw
text (that's planner/analyzer.py's job, tested separately in
test_analyzer.py with a fake LLM client, and ultimately needs a live
smoke test with a real OPENROUTER_API_KEY that only the project owner can
run in this environment).

Each hand-authored QueryRequirements represents a plausible, defensible
extraction of the scenario's query text — the same interpretation used to
manually validate the planner during development.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from capretrieve.manifest.loader import load_manifest_dir
from capretrieve.planner.planner import plan
from capretrieve.planner.models.requirements import (
    Freshness,
    ParadigmHint,
    PrivacySensitivity,
    QueryRequirements,
)

SCENARIOS_PATH = Path(__file__).parents[2] / "fixtures" / "scenarios.yaml"
CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"

# Hand-authored QueryRequirements per scenario id — see module docstring
# for why these are authored rather than LLM-derived in this test.
SCENARIO_REQUIREMENTS = {
    "S1": QueryRequirements(
        paradigm_hint=ParadigmHint.KEYWORD,
        relational=False,
        needs_freshness=Freshness.ANY,
        privacy_sensitivity=PrivacySensitivity.CONFIDENTIAL,
        expects_personal_knowledge=True,
    ),
    "S4": QueryRequirements(
        paradigm_hint=ParadigmHint.GRAPH_TRAVERSAL,
        relational=True,
        needs_freshness=Freshness.ANY,
        privacy_sensitivity=PrivacySensitivity.NONE,
        expects_personal_knowledge=True,
    ),
    "S5": QueryRequirements(
        paradigm_hint=ParadigmHint.DENSE_SEMANTIC,
        relational=False,
        needs_freshness=Freshness.ANY,
        privacy_sensitivity=PrivacySensitivity.NONE,
        expects_personal_knowledge=True,
    ),
}


def _load_scenarios() -> list[dict]:
    data = yaml.safe_load(SCENARIOS_PATH.read_text())
    return data["scenarios"]


def _manifests():
    return list(load_manifest_dir(CONFIG_DIR).values())


ALL_SCENARIOS = {s["id"]: s for s in _load_scenarios()}
ACTIVE_SCENARIO_IDS = [s["id"] for s in ALL_SCENARIOS.values() if s["status"] == "active"]
DEFERRED_SCENARIO_IDS = [
    s["id"] for s in ALL_SCENARIOS.values() if s["status"] == "deferred"
]


def test_fixture_has_expected_active_scenarios():
    """Guards against silently losing scenario coverage if the fixture
    changes shape."""
    assert set(ACTIVE_SCENARIO_IDS) == {"S1", "S4", "S5"}


def test_every_active_scenario_has_hand_authored_requirements():
    for scenario_id in ACTIVE_SCENARIO_IDS:
        assert scenario_id in SCENARIO_REQUIREMENTS, (
            f"{scenario_id} is active in fixtures/scenarios.yaml but has no "
            f"hand-authored QueryRequirements in this test file"
        )


@pytest.mark.parametrize("scenario_id", ["S1", "S4", "S5"])
def test_scenario_must_include(scenario_id):
    scenario = ALL_SCENARIOS[scenario_id]
    requirements = SCENARIO_REQUIREMENTS[scenario_id]

    result = plan(_manifests(), requirements)

    for connector_id in scenario["must_include"]:
        assert connector_id in result.selected_connector_ids, (
            f"{scenario_id}: expected {connector_id} to be selected, "
            f"got {result.selected_connector_ids}"
        )


@pytest.mark.parametrize("scenario_id", ["S1", "S4", "S5"])
def test_scenario_must_exclude(scenario_id):
    scenario = ALL_SCENARIOS[scenario_id]
    requirements = SCENARIO_REQUIREMENTS[scenario_id]

    result = plan(_manifests(), requirements)

    for exclusion in scenario["must_exclude"]:
        connector_id = exclusion["connector_id"]
        assert connector_id not in result.selected_connector_ids, (
            f"{scenario_id}: expected {connector_id} to be excluded, "
            f"but it was selected"
        )


@pytest.mark.parametrize("scenario_id", ["S1", "S4"])
def test_scenario_exclusion_is_hard_blocked_not_just_low_scored(scenario_id):
    """For scenarios whose must_exclude represents a HARD block (not just
    losing on score), confirm the decision trail shows admitted=False —
    this is what makes the exclusion reportable in the trace, per S1's
    requirement."""
    scenario = ALL_SCENARIOS[scenario_id]
    requirements = SCENARIO_REQUIREMENTS[scenario_id]

    result = plan(_manifests(), requirements)

    for exclusion in scenario["must_exclude"]:
        connector_id = exclusion["connector_id"]
        decision = result.decision_for(connector_id)
        assert decision is not None
        assert decision.admitted is False
        assert decision.exclusion_reason is not None


@pytest.mark.parametrize("scenario_id", ["S2", "S3"])
def test_deferred_scenarios_are_explicitly_skipped(scenario_id):
    """S2/S3 are known not to pass yet — deferred to later phases per the
    fixture's own status field. This test documents that fact rather than
    silently omitting them from the suite."""
    scenario = ALL_SCENARIOS[scenario_id]
    assert scenario["status"] == "deferred"
    pytest.skip(
        f"{scenario_id} deferred to phase {scenario['deferred_to_phase']}: "
        f"{scenario['note'].strip()}"
    )