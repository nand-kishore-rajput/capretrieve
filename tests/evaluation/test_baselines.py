"""Runner tests. Fake routers only: no LLM, no connectors, no network."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from capretrieve.evaluation.capretrieve_router import CapRetrieveRouter
from capretrieve.evaluation.records import RouteDecision, RunRecord, to_jsonable
from capretrieve.evaluation import runner
from capretrieve.evaluation.runner import Scenario, load_scenarios, run_batch

SCENARIOS = [Scenario("S1", "private query"), Scenario("S5", "semantic recall")]


class FakeRouter:
    def __init__(self, name: str, deterministic: bool, fail_on: str | None = None):
        self.name = name
        self.deterministic = deterministic
        self.model = None if deterministic else "fake-llm"
        self.fail_on = fail_on
        self.calls = 0

    async def route(self, query: str) -> RouteDecision:
        self.calls += 1
        if query == self.fail_on:
            raise RuntimeError("boom")
        return RouteDecision(selected=["chroma"], raw_output=query)


def _read(path: Path) -> list[RunRecord]:
    return [RunRecord.model_validate_json(l) for l in path.read_text().splitlines()]


async def test_stochastic_runs_n_times_deterministic_once(tmp_path):
    llm, kw = FakeRouter("llm", False), FakeRouter("kw", True)
    out = tmp_path / "b.jsonl"

    await run_batch(SCENARIOS, [llm, kw], n_runs=5, out_path=out, batch_id="b")

    records = _read(out)
    assert llm.calls == 10 and kw.calls == 2
    assert len(records) == 12
    assert {r.run_idx for r in records if r.router == "llm"} == set(range(5))
    assert all(r.batch_id == "b" and r.error is None for r in records)


async def test_router_exception_is_logged_not_raised(tmp_path):
    router = FakeRouter("llm", False, fail_on="private query")
    out = tmp_path / "b.jsonl"

    await run_batch(SCENARIOS, [router], n_runs=2, out_path=out, batch_id="b")

    by_scenario = {(r.scenario_id, r.run_idx): r for r in _read(out)}
    assert by_scenario[("S1", 0)].error == "RuntimeError: boom"
    assert by_scenario[("S1", 0)].selected == []
    assert by_scenario[("S5", 0)].error is None


async def test_resume_skips_successes_and_retries_failures(tmp_path):
    out = tmp_path / "b.jsonl"
    await run_batch(
        SCENARIOS, [FakeRouter("llm", False, fail_on="private query")],
        n_runs=3, out_path=out, batch_id="b",
    )

    healed = FakeRouter("llm", False)
    new = await run_batch(SCENARIOS, [healed], n_runs=3, out_path=out, batch_id="b")

    assert healed.calls == 3  # only the 3 failed S1 runs
    assert {r.scenario_id for r in new} == {"S1"}
    assert all(r.error is None for r in new)


GROQ_429 = (
    "LLM API error 429: Rate limit reached for model on tokens per minute (TPM): "
    "Limit 8000, Used 7939, Requested 671. Please try again in 4.575s."
)


class FlakyRouter(FakeRouter):
    def __init__(self, failures: int, message: str = GROQ_429):
        super().__init__("llm", False)
        self.failures, self.message = failures, message

    async def route(self, query: str) -> RouteDecision:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(self.message)
        return RouteDecision(selected=["chroma"])


async def test_rate_limit_is_retried_using_provider_hint(tmp_path, monkeypatch):
    waits: list[float] = []

    async def fake_sleep(s):
        waits.append(s)

    monkeypatch.setattr(runner, "_sleep", fake_sleep)
    router = FlakyRouter(failures=2)

    await run_batch(SCENARIOS[:1], [router], n_runs=1, out_path=tmp_path / "b.jsonl", batch_id="b")

    [rec] = _read(tmp_path / "b.jsonl")
    assert rec.error is None and rec.attempts == 3 and rec.selected == ["chroma"]
    assert waits == [pytest.approx(5.575), pytest.approx(5.575)]


async def test_non_rate_limit_error_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_sleep", lambda s: pytest.fail("should not sleep"))
    router = FlakyRouter(failures=1, message="ValidationError: bad JSON")

    await run_batch(SCENARIOS[:1], [router], n_runs=1, out_path=tmp_path / "b.jsonl", batch_id="b")

    [rec] = _read(tmp_path / "b.jsonl")
    assert rec.attempts == 1 and rec.error.endswith("bad JSON")


async def test_rate_limit_gives_up_after_max_attempts(tmp_path, monkeypatch):
    async def fake_sleep(s):
        pass

    monkeypatch.setattr(runner, "_sleep", fake_sleep)
    router = FlakyRouter(failures=99)

    await run_batch(SCENARIOS[:1], [router], n_runs=1, out_path=tmp_path / "b.jsonl", batch_id="b")

    [rec] = _read(tmp_path / "b.jsonl")
    assert rec.attempts == runner.MAX_ATTEMPTS and "429" in rec.error


async def test_capretrieve_router_logs_requirements_and_exclusions():
    class Sensitivity(enum.Enum):
        PERSONAL = "personal"

    @dataclass
    class Reqs:  # stands in for QueryRequirements (stdlib-only dataclass)
        privacy_sensitivity: Sensitivity
        relational: bool

    plan = SimpleNamespace(
        selected_connector_ids=["obsidian"],
        decisions=[
            SimpleNamespace(connector_id="obsidian", exclusion_reason=None),
            SimpleNamespace(
                connector_id="web_search",
                exclusion_reason=SimpleNamespace(constraint="privacy_leak"),
            ),
        ],
    )
    seen = {}

    def analyze(q):  # synchronous, like the real analyze(client, query)
        return Reqs(Sensitivity.PERSONAL, False)

    def fake_plan(manifests, requirements):  # real order: manifests first
        seen["manifests"], seen["requirements"] = manifests, requirements
        return plan

    router = CapRetrieveRouter(analyze, fake_plan, manifests=["m1"], model="m")
    d = await router.route("q")

    assert seen["manifests"] == ["m1"]
    assert isinstance(seen["requirements"], Reqs)
    assert d.selected == ["obsidian"]
    assert d.excluded == {"web_search": "privacy_leak"}
    assert d.requirements == {"privacy_sensitivity": "personal", "relational": False}


def test_to_jsonable_handles_pydantic():
    assert to_jsonable(RouteDecision(selected=["a"]))["selected"] == ["a"]


def test_load_scenarios_list_and_mapping_and_filter(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("scenarios:\n  - {id: S1, query: a}\n  - {id: S5, query: b}\n")
    assert [s.id for s in load_scenarios(f, only=["S5"])] == ["S5"]

    f.write_text("- {id: S1, query: a}\n")
    assert load_scenarios(f) == [Scenario("S1", "a")]

    with pytest.raises(KeyError):
        load_scenarios(f, only=["S9"])