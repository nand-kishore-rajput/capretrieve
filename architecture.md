# CapRetrieve — Architecture & File Reference

A guide to every code file in the project, organized by how data flows through
the system rather than alphabetically. Read top to bottom to follow the path a
query takes from HTTP request to synthesized answer.

---

## The one-paragraph mental model

A natural-language **query** comes in. An LLM **analyzer** turns it into a
structured `QueryRequirements` (what the query _needs_ — no connector names). The
**planner** matches those requirements against each connector's declared
`CapabilityManifest` (what each source _can do_) using typed fields only — never
prose — producing an `ExecutionPlan` (which connectors to query + why each was
kept or blocked). The **graph** fans out to the selected connectors in parallel,
each returning `Evidence`. **Fusion** dedups/normalizes/ranks that evidence into
one list. **Synthesis** (one LLM call) writes the final answer with per-claim
provenance. A **trace** records the whole decision path. The **API** exposes it.

The whole point: routing decisions are made by matching _structured metadata_,
not by asking an LLM "which tool should I use?" — that's what separates this from
LlamaIndex RouterQueryEngine / MCP tool-calling.

---

## 1. The data contracts (the vocabulary everything else speaks)

These define the shapes that flow between every component. Nothing here has
behavior — they're the typed nouns of the system.

| File                    | Purpose                                                                                                                                                                                                                                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest/models.py`    | **`CapabilityManifest`** + its enums (`Paradigm`, `Freshness`, `PrivacyTier`). The declaration of what one connector _can do_: its paradigm, data freshness, privacy tier, whether it leaks the query externally, and a doc-only `scope` string. This is the single most important type — the planner reads only these typed fields to route. |
| `manifest/loader.py`    | Loads `configs/connectors/*.yaml` into validated `CapabilityManifest` objects. The only place raw manifest YAML is parsed. Raises on duplicates or invalid files rather than silently dropping them.                                                                                                                                          |
| `manifest/errors.py`    | Error types for manifest loading/validation (`ManifestLoadError`, `ManifestValidationError`, `DuplicateConnectorIdError`).                                                                                                                                                                                                                    |
| `contracts/protocol.py` | **`Connector`** — the `Protocol` (structural interface) every connector must satisfy: `manifest()`, `retrieve()`, `health()`. This is what lets the graph treat Obsidian, Chroma, and web search identically.                                                                                                                                 |
| `contracts/request.py`  | **`RetrievalRequest`** — the normalized input to any connector's `retrieve()`: query, top_k, optional filters (e.g. `{"seed_note": ...}`), optional deadline.                                                                                                                                                                                 |
| `contracts/result.py`   | **`Evidence`** + **`RetrievalResult`** — the normalized output of any connector. Every `Evidence` carries `source_id` (provenance), content, score, uri. This is the common currency fusion operates on.                                                                                                                                      |
| `contracts/health.py`   | **`HealthStatus`** + `HealthState` (ok/degraded/down). What a connector reports about whether it's usable right now.                                                                                                                                                                                                                          |

---

## 2. The registry (what connectors exist)

| File                 | Purpose                                                                                                                                                                                                                                                                                                                                                                       |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `registry/static.py` | **`Registry`** — an explicit, in-memory `{connector_id: Connector}` map. Deliberately not a plugin/auto-discovery system. `build_registry()` loads manifests; `.register()` attaches a live connector to each (and rejects a connector whose manifest disagrees with its YAML). The planner reads `registry.manifests()`; the graph's retrieve step reads `registry.get(id)`. |
| `registry/errors.py` | Error types for registration/lookup (`UnknownConnectorIdError`, `ManifestConnectorMismatchError`, `ConnectorNotRegisteredError`).                                                                                                                                                                                                                                             |

---

## 3. The connectors (the actual data sources)

Each wraps an existing reader/client behind the `Connector` protocol. The planner
never imports these — it only sees their manifests.

| File                               | Purpose                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `connectors/obsidian/vault.py`     | Loads an Obsidian vault via LlamaIndex's `ObsidianReader`, then adds what that reader _doesn't_ do: parses YAML frontmatter and inline `#tags`. Produces `Note` objects with wikilinks/backlinks/tags/content.                                                                                                                                                       |
| `connectors/obsidian/traversal.py` | `expand_neighbourhood()` — from a seed note, walks outward via wikilinks + backlinks up to a given depth. This is the graph-traversal retrieval mode. (Note: treats the link graph as _undirected_.)                                                                                                                                                                 |
| `connectors/obsidian/connector.py` | **`ObsidianConnector`** — implements `Connector`. Two internal modes behind one interface: keyword/tag search (default), or seed-note graph traversal (when `filters={"seed_note": ...}` is present). Includes `_resolve_seed_note()` for fuzzy/case-insensitive matching of an LLM-extracted entity name to a real note title. Declares `paradigm=graph_traversal`. |
| `connectors/chroma/embeddings.py`  | **`HashingEmbeddingFunction`** — a deterministic, offline, dependency-free bag-of-words embedding. Used instead of ChromaDB's default (which downloads a model over the network). Swappable for a real embedding model without touching anything else.                                                                                                               |
| `connectors/chroma/ingest.py`      | `ingest_corpus()` — loads `fixtures/data/corpus/*.md` into a Chroma collection. Client is injectable (real `PersistentClient` in prod, `EphemeralClient` in tests — the latter avoids a known ChromaDB multi-instance hang). Disables ChromaDB telemetry.                                                                                                            |
| `connectors/chroma/connector.py`   | **`ChromaConnector`** — implements `Connector`. Dense semantic similarity search over the ingested collection. Converts Chroma's distance to a similarity-style score. Declares `paradigm=dense_semantic`.                                                                                                                                                           |
| `connectors/web/connector.py`      | **`WebSearchConnector`** — implements `Connector` over the Tavily search API. The only connector that leaves the local environment (`query_leaks_externally=true`), which is what the S1 privacy block keys on. Tavily client is injectable for testing. Declares `paradigm=keyword`.                                                                                |

---

## 4. The planner (the core thesis contribution)

Pure decision logic. **Never imports connectors or registry** — it receives
manifests as plain data. This is enforced by architecture tests. This is where
"structured metadata matching, not LLM tool-picking" actually lives.

| File                                        | Purpose                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `planner/models/requirements.py`            | **`QueryRequirements`** — the structured output of the analyzer: `paradigm_hint`, `relational`, `needs_freshness`, `privacy_sensitivity`, `expects_personal_knowledge`, `seed_entity`. The _only_ thing the planner sees about the query — never the raw text. Imports only stdlib (enforced).                                             |
| `planner/models/decision.py`                | **`SelectionDecision`** + **`ExclusionReason`** — the per-connector audit record: admitted (with score) or excluded (with a machine-checkable `constraint` string + human detail).                                                                                                                                                         |
| `planner/models/plan.py`                    | **`ExecutionPlan`** + **`PlanStep`** — the planner's final output: the ordered connectors to query (`steps`) plus the full decision trail for _every_ candidate (`decisions`), including the excluded ones. An empty plan is a valid, meaningful result.                                                                                   |
| `planner/analyzer.py`                       | `analyze()` — sends the query + the requirement-extraction prompt to an LLM, parses the response into `QueryRequirements`. The LLM client is injected. **Never sees connector names** (enforced).                                                                                                                                          |
| `planner/prompts/requirement_extraction.md` | The analyzer's prompt. Describes each `QueryRequirements` field in source-agnostic terms. Contains **no connector names or aliases** (enforced by a test) — mentioning a source here would smuggle tool-picking back in.                                                                                                                   |
| `planner/constraints.py`                    | The **hard filter**. Two rules (streamlined scope): privacy leak (`privacy_sensitivity != none` blocks any `query_leaks_externally` connector → S1) and paradigm fit (`relational=true` blocks any non-graph-traversal connector → S4). Each elimination produces an `ExclusionReason`. Reads only typed fields, never `scope` (enforced). |
| `planner/scoring.py`                        | The **soft score** over connectors that survived the hard filter. Small, declared (not learned) additive bonuses: paradigm match, personal-knowledge-wants-local, freshness match.                                                                                                                                                         |
| `planner/selection.py`                      | The **selection policy**: pick every candidate within `RELATIVE_THRESHOLD` of the top score. This is what makes a single-source query select one connector (S5, no over-selection) but a genuinely-comparable pair select both (S1).                                                                                                       |
| `planner/planner.py`                        | `plan()` — orchestrates filter → score → select over a list of manifests, producing the `ExecutionPlan`. Takes **manifests, not connectors** — so it structurally _cannot_ reach a connector, which is what keeps the architectural boundary honest rather than just documented.                                                           |

---

## 5. The LLM plumbing (shared by analyzer + synthesis)

| File                | Purpose                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `llm/client.py`     | **`OpenRouterClient`** — thin wrapper over OpenRouter's chat-completions endpoint via `httpx`. Sends a default `max_tokens` (Anthropic requires it). Raises `OpenRouterError` with the full response body on HTTP errors, and `EmptyCompletionError` (with a reasoning-token hint) when a 200 response has null content — both hard-learned from real end-to-end debugging. |
| `llm/structured.py` | `get_structured_output()` — takes any client, a prompt, and a Pydantic model; requests JSON, parses/validates it, and retries with a corrective follow-up on failure. Provider-agnostic (defines the `CompletesText` protocol). This is how the analyzer reliably gets a valid `QueryRequirements` back.                                                                    |

---

## 6. The orchestration graph (wiring it all together)

Built on LangGraph. Nodes are thin adapters — they unpack state, call the real
logic module, pack the result back. The graph is where the registry and
connectors are _allowed_ to meet the planner's output.

| File                        | Purpose                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `graph/state.py`            | **`GraphState`** — the shared state flowing through the pipeline (query, requirements, plan, raw evidence, fused evidence, answer). Uses a LangGraph `TypedDict` with an `operator.add` reducer on `raw_evidence` so parallel branches _accumulate_ rather than overwrite. Also **`RetrieveOneInput`** (the per-branch payload).                                                                                                              |
| `graph/build.py`            | `build_graph()` — assembles the pipeline: `analyze → plan → fan_out(retrieve) → fuse → synthesize`. Wires the injected registry and LLM clients into each node.                                                                                                                                                                                                                                                                               |
| `graph/nodes/analyze.py`    | Adapter → `planner.analyzer.analyze()`. Query in, `requirements` out.                                                                                                                                                                                                                                                                                                                                                                         |
| `graph/nodes/plan.py`       | Adapter → `planner.plan()`. **The wiring boundary**: it's allowed to read the registry's manifests and hand them to the (connector-blind) planner, keeping the planner's import isolation intact.                                                                                                                                                                                                                                             |
| `graph/nodes/retrieve.py`   | Two pieces: the **fan-out router** (empty plan → skip to fuse; otherwise one parallel `Send` per selected connector) and **`retrieve_one`** (looks up the actual connector and calls `retrieve()`). Also `_build_retrieval_filters()` — translates a relational query's `seed_entity` into the `{"seed_note": ..., "depth": 1}` filter that triggers Obsidian's graph-traversal mode. This is the only node that touches connectors directly. |
| `graph/nodes/fuse.py`       | Adapter → `fusion.merge.fuse()`.                                                                                                                                                                                                                                                                                                                                                                                                              |
| `graph/nodes/synthesize.py` | Adapter → `generation.synthesize.synthesize()`.                                                                                                                                                                                                                                                                                                                                                                                               |

---

## 7. Fusion (combining evidence — never calls an LLM)

Deterministic operations over `Evidence`. The "no LLM in fusion" rule is enforced
by an architecture test — fusion ranks, it doesn't reason.

| File                  | Purpose                                                                                                                                                           |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fusion/normalize.py` | `normalize_scores()` — min-max normalizes scores **per source**, since a Chroma cosine score and an Obsidian keyword-hit count aren't on the same scale.          |
| `fusion/dedup.py`     | `dedup()` — removes exact `(source_id, uri)` duplicates, keeping the highest-scoring instance. Does **not** merge across sources (that would destroy provenance). |
| `fusion/merge.py`     | `fuse()` — the single entry point: dedup → normalize → sort by score → optional cap. Produces the final ranked, provenance-preserving evidence list.              |

---

## 8. Generation (the final answer)

| File                              | Purpose                                                                                                                                                                                                               |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `generation/synthesize.py`        | `synthesize()` — one LLM call that turns fused evidence + the query into a final answer with inline `[source_id: uri]` citations per claim. The _only_ place an LLM call happens after retrieval. Client is injected. |
| `generation/prompts/synthesis.md` | The synthesis prompt. Instructs the model to answer only from provided evidence, cite each claim's source, and say so plainly if evidence is insufficient.                                                            |

---

## 9. The trace (the demo artifact)

| File                | Purpose                                                                                                                                                                                                                                             |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `trace/models.py`   | **`PlanTrace`** + `ConnectorExecutionRecord` — the full decision path for one query: requirements → every candidate's decision (+block reason) → per-connector execution counts → fused evidence → answer. "The code isn't the demo; the trace is." |
| `trace/recorder.py` | `build_trace()` — assembles a `PlanTrace` from a completed `GraphState`. (Includes the `answer or ""` guard for a null LLM completion.)                                                                                                             |
| `trace/render.py`   | Renders a `PlanTrace` as JSON or as dependency-free, HTML-escaped HTML — a human-readable "why did it do that" view, no frontend framework.                                                                                                         |

---

## 10. The API (the entry point)

| File                       | Purpose                                                                                                                                     |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `api/schemas.py`           | Request/response Pydantic models: `QueryRequest`, `QueryResponse` (answer + evidence + plan_trace), `ConnectorsResponse`, health schemas.   |
| `api/routes/query.py`      | `POST /query` — runs the graph on the query, builds the trace, returns answer + evidence + trace.                                           |
| `api/routes/connectors.py` | `GET /connectors` — returns the raw manifests (what each source declares it can do).                                                        |
| `api/routes/health.py`     | `GET /health` — aggregates every connector's `health()` into one response.                                                                  |
| `api/app.py`               | `create_app()` — the FastAPI app factory. Takes an already-built registry + graph, so it's testable with fakes. Stores them on `app.state`. |
| `api/main.py`              | The uvicorn entrypoint (`uvicorn capretrieve.api.main:app`). Calls `bootstrap.build_default_app()`.                                         |

---

## 11. Wiring & configuration (turning parts into a running system)

| File           | Purpose                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `settings.py`  | **`Settings`** — all runtime config from environment variables: OpenRouter key + model slugs, Tavily key, data directories, query defaults. `require_openrouter_api_key()` fails fast if the one required secret is missing.                                                                                                                                        |
| `bootstrap.py` | The real assembly layer. `build_default_registry()` constructs the three real connectors from settings; `build_default_graph()` / `build_default_app()` wire them to real `OpenRouterClient`s. This is where the three external integrations (Tavily + two OpenRouter calls) are finally instantiated for real. Chroma client is injectable so this stays testable. |

---

## 12. Config, fixtures, and project files (data, not code)

| File                                                   | Purpose                                                                                                                                                                                    |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `configs/connectors/{obsidian,chroma,web_search}.yaml` | The three connector manifests **as data**. Editing a field here changes routing behavior with zero code changes — the property the whole design rests on.                                  |
| `fixtures/scenarios.yaml`                              | The five adversarial scenarios (S1–S5) as ground truth: each query's `must_include` / `must_exclude` with machine-checkable exclusion reasons. S1/S4/S5 active; S2/S3 deferred to Phase 6. |
| `fixtures/data/vault/*.md`                             | Sample Obsidian vault (4 linked notes) the Obsidian connector runs against in dev/test.                                                                                                    |
| `fixtures/data/corpus/*.md`                            | Sample document corpus the Chroma connector ingests in dev/test.                                                                                                                           |
| `pyproject.toml`                                       | Package metadata, dependencies, pytest config.                                                                                                                                             |
| `Dockerfile` / `docker-compose.yml`                    | Container build (editable install) and run (bind-mount + port mapping).                                                                                                                    |
| `.env.example`                                         | Template for the environment variables `settings.py` reads.                                                                                                                                |

---

## The five architectural invariants (enforced by CI tests)

These are the guardrails that keep the project from quietly degrading into
"RouterQueryEngine with extra steps." Each has a test in `tests/architecture/`:

1. The planner never imports `connectors/` or `registry/`.
2. `planner/models/` imports only `manifest/` + stdlib.
3. The analyzer prompt contains no connector names.
4. The `scope` field is never read by planner code.
5. Fusion never calls an LLM.

---

## Query flow, end to end

```
HTTP POST /query
  → api/routes/query.py
    → graph (graph/build.py)
      → analyze node    → planner/analyzer.py  → QueryRequirements
      → plan node       → planner/planner.py   → ExecutionPlan
                          (constraints → scoring → selection over manifests)
      → fan-out router  → one parallel Send per selected connector
        → retrieve_one  → registry.get(id).retrieve()  → Evidence[]
      → fuse node       → fusion/merge.py       → ranked Evidence[]
      → synthesize node → generation/synthesize.py → answer w/ citations
    → trace/recorder.py → PlanTrace
  → QueryResponse {answer, evidence, plan_trace}
```
