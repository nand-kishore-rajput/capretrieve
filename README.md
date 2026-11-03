# CapRetrieve

**Capability-aware query routing across heterogeneous knowledge sources.**

When a retrieval system can search your private notes, a local document
collection and the live web, the riskiest decision comes before retrieval:
*where should this query go?* Most systems hand that choice to an LLM reading
free-text tool descriptions. CapRetrieve splits it in two:

- **An LLM describes the query.** It turns the question into typed
  requirements (privacy sensitivity, freshness, retrieval style, whether it
  is about the user's own notes) and never sees which sources exist.
- **Deterministic rules choose the source.** A planner matches those
  requirements against each source's typed capability manifest: hard filter,
  then score, then select. Every decision, including why a source was
  blocked, is recorded in a plan trace.

So a rule like "never send a confidential query to the web" is enforced in
code, not requested in a prompt.

```
"We agreed 40 million for Project Falcon. Has anything leaked in the press?"

  analyzer  ->  privacy_sensitivity=confidential, needs_freshness=live, ...
  planner   ->  obsidian  selected
                chroma    selected
                web_search BLOCKED  privacy_leak: privacy_sensitivity=confidential
                                    and query_leaks_externally=true on web_search
  answer    ->  cited only from local sources
```

## Quickstart (local, Python 3.11+)

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env          # then set OPENROUTER_API_KEY (or LLM_API_KEY)
.venv/bin/uvicorn capretrieve.api.main:app --port 8000
```

Open **http://localhost:8000/demo**, type a question or click an example, and
press Execute. The repo ships demo data in `fixtures/data/`, so this works
out of the box: a 30-note linked Obsidian vault for a fictional user and a
20-document reference corpus.

`instructions.md` covers the container setup used on the DFKI server.

## What you can look at

A 2-minute screen recording of the `/demo` page answering example
questions: [docs/demo-recording.mp4](docs/demo-recording.mp4).

| Endpoint      | What it shows                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------- |
| `/demo`       | Question box with examples. Shows the analyzer's reading, each source's decision, answer, evidence |
| `/trace/view` | The same trace as a static HTML page, opened by URL (needs `TRACE_VIEW_TOKEN`)                     |
| `POST /query` | JSON: `answer`, `evidence[]`, `plan_trace`                                                         |
| `POST /trace` | Routing trace only, without the answer step (one LLM call)                                         |
| `/connectors` | The capability manifests every source declares                                                     |
| `/health`     | Per-source health                                                                                  |
| `/docs`       | Swagger UI                                                                                         |

## Configuration

All settings come from environment variables or `.env`. An empty value
counts as unset.

| Variable                          | Default                                       | Purpose                                                                                |
| --------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------- |
| `LLM_API_BASE`                    | `https://openrouter.ai/api/v1`                | Any OpenAI-compatible endpoint (OpenRouter, Groq, a local server)                      |
| `LLM_API_KEY` / `OPENROUTER_API_KEY` | (required)                                 | Key for that endpoint                                                                  |
| `ANALYZER_MODEL`                  | `openrouter/free`                             | Model that extracts requirements                                                       |
| `SYNTHESIS_MODEL`                 | `openrouter/free`                             | Model that writes the answer                                                           |
| `LLM_MAX_TOKENS`                  | `4096`                                        | Raise it for reasoning models, which can spend the budget before answering             |
| `WEB_SEARCH_API_KEY`              | (unset: keyless, rate-limited)                | Tavily key                                                                             |
| `TRACE_VIEW_TOKEN`                | (unset: `/trace/view` disabled)               | Shared secret for `/trace/view`                                                        |
| `VAULT_DIR` / `CORPUS_DIR`        | `fixtures/data/vault`, `fixtures/data/corpus` | Your own Obsidian vault and document folder                                            |
| `CONFIG_DIR`                      | `configs/connectors`                          | Where the capability manifests live                                                    |
| `CHROMA_PERSIST_DIR`              | `.chroma`                                     | Chroma index location                                                                  |
| `EMBEDDING_MODEL`                 | (unset: offline hashing embedding)            | A sentence-transformers model name for real semantic embeddings                        |
| `DEFAULT_TOP_K` / `MAX_FUSED_ITEMS` | `5` / `10`                                  | Results per source, and the cap after fusion                                           |

`openrouter/free` routes each call to a random free model, so results vary
between runs and calls can be slow or rate-limited. Pin a model for demos.

## Adding your own source

A source is a YAML capability manifest plus a small Python class with three
methods. Nothing in the planner changes. See
[docs/adding-a-connector.md](docs/adding-a-connector.md).

## Documentation

| Document                                                 | Read it for                                                            |
| -------------------------------------------------------- | ---------------------------------------------------------------------- |
| [docs/positioning.md](docs/positioning.md)               | The problem, how this differs from LLM tool calling, evaluation results |
| [docs/architecture.md](docs/architecture.md)             | The pipeline, components, invariants and failure handling              |
| [docs/capretrieve-query-flow.pdf](docs/capretrieve-query-flow.pdf) | Illustrated walkthrough of one query through every stage              |
| [docs/manifest-schema.md](docs/manifest-schema.md)       | Every manifest and requirement field, and the exact planner rules       |
| [docs/adding-a-connector.md](docs/adding-a-connector.md) | Step-by-step guide to plugging in a new source                         |
| [docs/evaluation.md](docs/evaluation.md)                 | Scenarios, baselines, and how to run and replay the evaluation          |
| [docs/demo-guide.md](docs/demo-guide.md)                 | Running a ten-minute team demo, with questions and talking points       |
| [docs/future-work.md](docs/future-work.md)               | Known limitations and planned extensions                               |
| [docs/decisions/](docs/decisions/)                       | Design decision records                                                |
| [architecture.md](architecture.md)                       | File-by-file reference, following a query through the code             |

## Tests

```bash
.venv/bin/python -m pytest -q
```

Architecture tests in `tests/architecture/` enforce the design boundaries:
the planner never imports connectors, the analyzer prompt names no source,
and the planner never reads free-text descriptions. Scenario tests in
`tests/scenarios/` check routing against `fixtures/scenarios.yaml`.

## License

MIT, see [LICENSE](LICENSE).
