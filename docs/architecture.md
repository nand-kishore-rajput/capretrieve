# Architecture

This page explains how CapRetrieve is put together and why. For a
file-by-file walk through the code, see the root
[architecture.md](../architecture.md). For the exact routing rules, see
[manifest-schema.md](manifest-schema.md). For an illustrated walkthrough of one query
through every stage, with a worked example, see
[capretrieve-query-flow.pdf](capretrieve-query-flow.pdf).

## The pipeline

```
                    ┌──────────────────────────────┐
  question ───────► │ analyze   (LLM, source-blind) │ ──► QueryRequirements
                    └──────────────────────────────┘
                                   │
     configs/connectors/*.yaml     ▼
     (capability manifests) ─► ┌──────────────────────────────┐
                               │ plan  filter → score → select │ ──► ExecutionPlan
                               └──────────────────────────────┘     (steps + every decision)
                                   │
                     one parallel branch per selected source
                 ┌─────────────────┼─────────────────┐
                 ▼                 ▼                 ▼
            obsidian           chroma          web_search      ──► Evidence[] per source
                 └─────────────────┼─────────────────┘                (or an error record)
                                   ▼
                    ┌──────────────────────────────┐
                    │ fuse   dedup → normalise →    │ ──► ranked Evidence[]
                    │        sort → cap  (no LLM)   │
                    └──────────────────────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │ synthesize  (LLM)             │ ──► answer with [source_id: uri] citations
                    └──────────────────────────────┘
                                   ▼
                              PlanTrace
```

The pipeline is a LangGraph state graph (`graph/build.py`). Nodes are thin
adapters around plain modules (`planner/`, `fusion/`, `generation/`), so each
step is testable without the graph.

A second graph, `build_trace_graph`, stops after `fuse`. `POST /trace` uses
it to return a routing trace with a single LLM call (the analyzer). The
evaluation package uses the same split.

## Components

### Analyzer (`planner/analyzer.py`)

One LLM call with the prompt in `planner/prompts/requirement_extraction.md`.
It returns `QueryRequirements`, a Pydantic model of enums, booleans and one
optional string. `llm/structured.py` validates the JSON and retries once with
a corrective message on failure, up to two extra attempts.

The analyzer sees only the query and the requirements schema. It never sees
connector names, manifests or the registry. This is the most important
isolation in the system: an analyzer that knows which sources exist can drift
back into picking tools.

### Capability manifests (`manifest/`, `configs/connectors/`)

Each source declares what it can do as data: `paradigm`, `freshness`,
`privacy_tier`, `query_leaks_externally`, and a free-text `scope` for
humans. `manifest/loader.py` is the only place YAML is parsed. It rejects
invalid files and duplicate ids rather than skipping them.

### Planner (`planner/planner.py`, `constraints.py`, `scoring.py`, `selection.py`)

Pure functions over typed data. `plan()` takes a list of manifests and the
requirements, not connectors, so it structurally cannot call a source.

1. **Filter.** Hard constraints remove sources that must not be used. Each
   removal records a stable `constraint` id and a human-readable `detail`.
2. **Score.** Remaining sources get small, declared, additive bonuses.
3. **Select.** Force-include rules, then a relative threshold over the top
   score.

An empty plan, where every source was blocked, is a valid result. It is
reported in the trace, not raised as an error.

### Registry (`registry/static.py`)

An explicit `{connector_id: Connector}` map built at startup. Manifests come
from YAML. Each live connector is attached with `register()`, which rejects a
connector whose `manifest()` disagrees with its YAML. There is deliberately
no plugin discovery: adding a source is a visible, reviewed code change (see
[adding-a-connector.md](adding-a-connector.md)).

### Connectors (`connectors/`)

Every source implements the same three-method `Connector` protocol
(`contracts/protocol.py`):

| Connector    | Backed by                                  | Paradigm          | Notes                                                                                                  |
| ------------ | ------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------ |
| `obsidian`   | LlamaIndex `ObsidianReader` + frontmatter/tag parsing | `graph_traversal` | Keyword search by default; breadth-first link traversal from a seed note when the query is relational. Reloads on the next query when a note is edited, added or deleted. |
| `chroma`     | ChromaDB                                   | `dense_semantic`  | Corpus ingested at startup, one document per file. Offline hashing embedding unless `EMBEDDING_MODEL` is set. |
| `web_search` | Tavily                                     | `keyword`         | The only source that sends the query outside the machine (`query_leaks_externally: true`).            |

Blocking client calls (Tavily, the LLM HTTP calls) run in worker threads,
so one slow query does not stall the server.

### Fusion (`fusion/`)

Deterministic and LLM-free (enforced by a test). It removes exact
`(source_id, uri)` duplicates, min-max normalises scores per source (a cosine
similarity and a keyword hit count are not on the same scale), sorts, and
caps the list at `MAX_FUSED_ITEMS`. It never merges across sources, so each
item keeps its provenance.

### Synthesis (`generation/`)

One LLM call that answers only from the fused evidence and cites each claim
as `[source_id: uri]`. With no evidence it returns a fixed "no permitted
source returned evidence" message without calling the LLM, so a
privacy-blocked query is not sent to the provider for nothing.

### Trace (`trace/`)

`PlanTrace` records the query, the requirements, every candidate's decision
(admitted with a score, or excluded with a reason), per-source execution
(result count and any error), the fused evidence and the answer.
`trace/render.py` renders it as HTML for `/trace/view`. The `/demo` page
renders the same data in the browser from `POST /query`.

## User-facing surfaces

| Surface       | Use it when                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------------- |
| `/demo`       | Showing the system to people: question box, example questions, decisions, answer and evidence on one page. No token needed: the page only spends credits when submitted, and the submit is a JSON POST other sites cannot send. |
| `/trace/view` | Sharing or bookmarking a trace as a static page. It is a GET that spends credits, so it requires `TRACE_VIEW_TOKEN`. |
| `POST /query`, `POST /trace` | Programmatic use and evaluation.                                                    |
| `/connectors`, `/health`     | Inspecting what each source declares and whether it is up.                          |

## Failure handling

- **A source fails during retrieval.** The error is recorded for that
  source, shown in the trace's Execution section, and the query continues
  with the other sources.
- **Every source is blocked.** The plan is empty, retrieval and synthesis
  are skipped, and the answer says no permitted source returned evidence.
- **The LLM returns no usable output.** `llm/client.py` raises a specific
  error: `EmptyCompletionError` when a reasoning model spent `max_tokens`
  before answering, `LLMError` on HTTP errors or a response without choices.
  The request fails with a 500 and the reason in the server log.
- **A manifest exists with no registered connector.** Selecting it fails the
  request. Every YAML manifest must have a matching `register()` call.

## Architectural invariants

These keep the project from sliding back into "an LLM picks the tool". Most
are executable tests:

| Invariant                                                            | Enforced by                                        |
| -------------------------------------------------------------------- | -------------------------------------------------- |
| The planner never imports `connectors/` or `registry/`               | `tests/architecture/test_planner_imports.py`       |
| `planner/models/` imports only `manifest/`, Pydantic and stdlib      | `tests/architecture/test_planner_models_pure.py`   |
| The analyzer prompt names no connector id or alias                   | `tests/architecture/test_analyzer_isolation.py`    |
| Planner code never reads the free-text `scope` field                 | `tests/architecture/test_no_freetext_in_planner.py` |
| Fusion never imports an LLM or network client                        | `tests/architecture/test_fusion_has_no_llm.py`     |
| Editing a manifest YAML changes the plan with no code change         | `tests/scenarios/test_manifest_sensitivity.py`     |
| Graph nodes stay thin; logic lives in plain modules                  | Code review (`test_nodes_are_thin.py` is still empty) |

## Design decisions

- **Rules, not judgement, for selection.** The LLM's output is limited to a
  small typed vocabulary. Everything after that is inspectable code.
- **Declared, not learned, weights.** The scoring bonuses are hand-set
  constants in `planner/scoring.py`. They are few enough to reason about,
  and the ablation shows the result does not depend on fine-tuning them.
  Learning them from usage is future work.
- **An explicit registry, not a plugin system.** New sources are added in
  reviewed code, and the registry checks that each connector agrees with its
  manifest.
- **Scenarios, not a benchmark.** `fixtures/scenarios.yaml` is a
  specification of what the planner must do, with a machine-checkable reason
  for every exclusion. The evaluation measures routing correctness against
  it, not answer quality.
- **Provider-agnostic LLM client.** Any OpenAI-compatible endpoint works
  through `LLM_API_BASE`, including a local model, which closes the gap
  where query text leaves the machine for the LLM calls.
