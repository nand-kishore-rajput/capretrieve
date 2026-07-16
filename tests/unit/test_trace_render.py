"""
Tests for trace/render.py — JSON and HTML rendering of a PlanTrace.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from capretrieve.contracts.result import Evidence
from capretrieve.planner.models.decision import ExclusionReason, SelectionDecision
from capretrieve.planner.models.plan import ExecutionPlan, PlanStep
from capretrieve.planner.models.requirements import QueryRequirements
from capretrieve.trace.models import ConnectorExecutionRecord, PlanTrace
from capretrieve.trace.render import render_html, render_json


def _ev(source_id: str, uri: str, content: str = "content") -> Evidence:
    return Evidence(
        source_id=source_id,
        content=content,
        score=0.75,
        uri=uri,
        retrieved_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_trace() -> PlanTrace:
    plan = ExecutionPlan(
        steps=[PlanStep(connector_id="chroma", score=1.5)],
        decisions=[
            SelectionDecision(connector_id="chroma", admitted=True, score=1.5),
            SelectionDecision(
                connector_id="web_search",
                admitted=False,
                exclusion_reason=ExclusionReason(
                    connector_id="web_search",
                    constraint="privacy_leak",
                    detail="privacy_sensitivity=confidential and query_leaks_externally=true",
                ),
            ),
        ],
    )
    return PlanTrace(
        query="my distinctive test query",
        requirements=QueryRequirements(),
        execution_plan=plan,
        execution=[ConnectorExecutionRecord(connector_id="chroma", evidence_count=2)],
        fused_evidence=[_ev("chroma", "fixtures/data/corpus/x.md")],
        answer="a distinctive final answer",
    )


def test_render_json_is_valid_json(sample_trace):
    output = render_json(sample_trace)
    parsed = json.loads(output)
    assert parsed["query"] == "my distinctive test query"
    assert parsed["answer"] == "a distinctive final answer"


def test_render_json_round_trips_through_pydantic(sample_trace):
    output = render_json(sample_trace)
    reconstructed = PlanTrace.model_validate_json(output)
    assert reconstructed == sample_trace


def test_render_html_contains_query(sample_trace):
    html_out = render_html(sample_trace)
    assert "my distinctive test query" in html_out


def test_render_html_contains_answer(sample_trace):
    html_out = render_html(sample_trace)
    assert "a distinctive final answer" in html_out


def test_render_html_shows_selected_connector(sample_trace):
    html_out = render_html(sample_trace)
    assert "chroma" in html_out
    assert "admitted" in html_out


def test_render_html_shows_exclusion_reason(sample_trace):
    html_out = render_html(sample_trace)
    assert "privacy_leak" in html_out
    assert "query_leaks_externally=true" in html_out


def test_render_html_escapes_hostile_content_in_query():
    plan = ExecutionPlan(steps=[], decisions=[])
    trace = PlanTrace(
        query="<script>alert('xss')</script>",
        requirements=QueryRequirements(),
        execution_plan=plan,
        execution=[],
        fused_evidence=[],
        answer="",
    )
    html_out = render_html(trace)
    assert "<script>alert" not in html_out
    assert "&lt;script&gt;" in html_out


def test_render_html_escapes_hostile_content_in_evidence():
    plan = ExecutionPlan(steps=[], decisions=[])
    trace = PlanTrace(
        query="q",
        requirements=QueryRequirements(),
        execution_plan=plan,
        execution=[],
        fused_evidence=[_ev("chroma", "u1", content="<img src=x onerror=alert(1)>")],
        answer="",
    )
    html_out = render_html(trace)
    assert "<img src=x" not in html_out


def test_render_html_is_well_formed_enough_to_have_matching_tags(sample_trace):
    html_out = render_html(sample_trace)
    assert html_out.count("<table>") == html_out.count("</table>")
    assert html_out.count("<html>") == 1
    assert html_out.count("</html>") == 1