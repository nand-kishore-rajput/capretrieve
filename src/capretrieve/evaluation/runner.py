"""
Evaluation runner: scenarios x routers x N runs -> one JSONL log per batch.

    python -m capretrieve.evaluation.runner --runs 10
    python -m capretrieve.evaluation.runner --runs 1 --scenarios S5 --batch-id smoke

- Stochastic routers (LLM-based) run N times per scenario; deterministic
  ones run once.
- Every run is appended and flushed as soon as it finishes, so a crash
  loses nothing. Re-running with the same --batch-id resumes: successful
  runs are skipped, failed ones are retried.
- A failing run is logged with `error` set; the batch carries on.
- All scenarios run, including known gaps (S2/S3). compare.py decides
  what is expected to fail.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from capretrieve.evaluation.records import Router, RunRecord

# This file lives at <repo>/src/capretrieve/evaluation/runner.py, so the repo
# root is three levels up. Paths below don't depend on the working directory.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIOS = REPO_ROOT / "fixtures" / "scenarios.yaml"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "reports" / "runs"


@dataclass(frozen=True)
class Scenario:
    id: str
    query: str


def load_scenarios(path: Path, only: Sequence[str] | None = None) -> list[Scenario]:
    data = yaml.safe_load(path.read_text())
    items = data["scenarios"] if isinstance(data, dict) else data
    scenarios = [Scenario(id=str(s["id"]), query=s["query"]) for s in items]
    if only:
        wanted = set(only)
        missing = wanted - {s.id for s in scenarios}
        if missing:
            raise KeyError(f"unknown scenario ids: {sorted(missing)}")
        scenarios = [s for s in scenarios if s.id in wanted]
    return scenarios


def _completed_keys(out_path: Path) -> set[tuple[str, str, int]]:
    """(scenario, router, run_idx) already logged without error."""
    if not out_path.exists():
        return set()
    done = set()
    for line in out_path.read_text().splitlines():
        if not line.strip():
            continue
        r = RunRecord.model_validate_json(line)
        if r.error is None:
            done.add((r.scenario_id, r.router, r.run_idx))
    return done


MAX_ATTEMPTS = 8
_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)\s*(ms|s)", re.IGNORECASE)
_sleep = asyncio.sleep  # module-level so tests can replace it


def _rate_limit_wait(exc: Exception, attempt: int) -> float | None:
    """Seconds to wait if exc is a rate limit (HTTP 429), else None.

    Uses the provider's own "try again in Xs" hint when present, plus a small
    margin; otherwise exponential backoff capped at 60s.
    """
    msg = str(exc)
    if "429" not in msg and "rate limit" not in msg.lower():
        return None
    m = _RETRY_AFTER_RE.search(msg)
    if m:
        wait = float(m.group(1)) / (1000 if m.group(2).lower() == "ms" else 1)
        return wait + 1.0
    return min(60.0, 2.0 * 2**attempt)


async def _run_one(
    router: Router, scenario: Scenario, run_idx: int, batch_id: str
) -> RunRecord:
    common = dict(
        batch_id=batch_id,
        scenario_id=scenario.id,
        router=router.name,
        run_idx=run_idx,
        model=router.model,
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        # latency covers the successful attempt only, not time spent waiting
        start = time.perf_counter()
        try:
            d = await router.route(scenario.query)
            break
        except Exception as exc:  # recorded, never raised: one bad run != dead batch
            wait = _rate_limit_wait(exc, attempt)
            if wait is None or attempt == MAX_ATTEMPTS:
                return RunRecord(
                    **common,
                    attempts=attempt,
                    error=f"{type(exc).__name__}: {exc}",
                    latency_ms=(time.perf_counter() - start) * 1000,
                    timestamp=datetime.now(timezone.utc),
                )
            await _sleep(wait)
    return RunRecord(
        **common,
        attempts=attempt,
        selected=d.selected,
        excluded=d.excluded,
        invalid=d.invalid,
        requirements=d.requirements,
        raw_output=d.raw_output,
        latency_ms=(time.perf_counter() - start) * 1000,
        timestamp=datetime.now(timezone.utc),
    )


async def run_batch(
    scenarios: Sequence[Scenario],
    routers: Sequence[Router],
    n_runs: int,
    out_path: Path,
    batch_id: str,
    concurrency: int = 4,
) -> list[RunRecord]:
    """Run every pending job, append each record to out_path, return new records."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = _completed_keys(out_path)

    jobs = [
        (router, scenario, i)
        for router in routers
        for scenario in scenarios
        for i in range(1 if router.deterministic else n_runs)
        if (scenario.id, router.name, i) not in done
    ]

    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    records: list[RunRecord] = []

    with out_path.open("a") as fh:

        async def worker(router: Router, scenario: Scenario, i: int) -> None:
            async with sem:
                rec = await _run_one(router, scenario, i, batch_id)
            async with write_lock:
                fh.write(rec.model_dump_json() + "\n")
                fh.flush()
                records.append(rec)

        await asyncio.gather(*(worker(*job) for job in jobs))

    return records


def summarize(records: Sequence[RunRecord]) -> str:
    ok, err = Counter(), Counter()
    for r in records:
        (err if r.error else ok)[r.router] += 1
    lines = [f"{name:<22} ok={ok[name]:<4} error={err[name]}" for name in sorted(ok | err)]
    first_errors = {r.router: r.error for r in records if r.error}
    lines += [f"  first error [{k}]: {v}" for k, v in first_errors.items()]
    return "\n".join(lines) or "nothing to run (batch already complete)"


# Router factories, keyed by CLI name. Imported lazily so a missing API key
# for one router doesn't stop the others from running.
def _router_factories() -> dict[str, Callable[[], Router]]:
    from capretrieve.evaluation.baselines.keyword_router import build_keyword_router
    from capretrieve.evaluation.baselines.tool_description_router import (
        build_tool_description_policy_router,
        build_tool_description_router,
    )
    from capretrieve.evaluation.capretrieve_router import build_capretrieve_router

    return {
        "capretrieve": build_capretrieve_router,
        "keyword": build_keyword_router,
        "tool_description": build_tool_description_router,
        "tool_description_policy": build_tool_description_policy_router,
    }


def main(argv: Sequence[str] | None = None) -> None:
    from dotenv import load_dotenv

    load_dotenv()
    factories = _router_factories()

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--runs", type=int, default=10, help="runs per stochastic router")
    p.add_argument("--routers", default=",".join(factories), help="comma-separated")
    p.add_argument("--scenarios", default="", help="comma-separated ids (default: all)")
    p.add_argument("--scenarios-file", type=Path, default=DEFAULT_SCENARIOS)
    p.add_argument("--batch-id", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    # Low default: Groq's free tier is limited by tokens per minute, so more
    # parallel calls only produce more 429s. Rate-limited calls are retried.
    p.add_argument("--concurrency", type=int, default=2)
    args = p.parse_args(argv)

    names = [n.strip() for n in args.routers.split(",") if n.strip()]
    unknown = set(names) - set(factories)
    if unknown:
        p.error(f"unknown routers {sorted(unknown)}; available: {sorted(factories)}")

    only = [s.strip() for s in args.scenarios.split(",") if s.strip()] or None
    scenarios = load_scenarios(args.scenarios_file, only)
    routers = [factories[n]() for n in names]
    out_path = args.out_dir / f"{args.batch_id}.jsonl"

    records = asyncio.run(
        run_batch(scenarios, routers, args.runs, out_path, args.batch_id, args.concurrency)
    )
    print(summarize(records))
    print(f"log: {out_path}")


if __name__ == "__main__":
    main()