# 0001: LangGraph for orchestration, LlamaIndex only as a library

**Status:** accepted

## Context

The pipeline runs analyze, plan, retrieve, fuse and synthesize. The retrieve
step fans out to a set of sources the planner chooses per query, so the
number of parallel branches is only known at runtime. Results from those
branches have to accumulate into shared state, and the whole decision path
has to be recorded for the trace.

LlamaIndex offers `RouterQueryEngine`, which routes by asking an LLM to pick
from free-text tool descriptions. That is the pattern this project sets out
to replace, so its router can't be the core of the system.

## Decision

- Orchestrate with a LangGraph `StateGraph` (`graph/build.py`). The fan-out
  uses LangGraph's `Send`, one branch per selected connector, and
  `GraphState.raw_evidence` uses an `operator.add` reducer so parallel
  branches append instead of overwriting.
- Use LlamaIndex only where it saves real work: `ObsidianReader` loads the
  vault and extracts wikilinks and backlinks (`connectors/obsidian/vault.py`).
  Its routing and query-engine layers are not used.

## Consequences

- Routing logic lives in plain modules (`planner/`), not in the framework.
  Graph nodes are thin adapters, so the planner is testable without the
  graph.
- A second graph that stops after fusion (`build_trace_graph`) is a few
  lines, which gives `POST /trace` and the evaluation a one-LLM-call path.
- The project depends on LangGraph's `Send` and reducer semantics for its
  fan-out.
