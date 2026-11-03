# Adding your own source

A source (a "connector") is two things:

1. a **capability manifest** in `configs/connectors/<id>.yaml` that
   declares what the source can do, and
2. a **Python class** with three methods that does the retrieval.

You don't change the planner, the analyzer or the graph. The planner routes
to your source purely from its manifest, the same way it routes to the
built-in ones.

This guide adds an example source called `bookmarks`, a local JSON file of
saved links searched by keyword, and covers every place the project needs
to know about it.

## 1. Declare the capabilities

Answer four questions about the source. Each answer is a manifest field the
planner acts on (full rules in [manifest-schema.md](manifest-schema.md)):

| Question                                                      | Field                    | Effect on routing                                                                 |
| ------------------------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------- |
| How does it find things: by meaning, by links, or by words?   | `paradigm`               | +1.0 when it matches the query's style. Only `graph_traversal` survives a relational query. |
| How current is its data?                                      | `freshness`              | `live` sources get +0.3 and are force-included for recent/live questions          |
| Is the data the user's own and under their control?          | `privacy_tier`           | `private_local` sources get +0.5 and are force-included for questions about the user's own knowledge |
| Does calling it send the query text to a third party?         | `query_leaks_externally` | `true` blocks the source for every sensitive query. **Be honest here:** this flag is the privacy guarantee. |

`configs/connectors/bookmarks.yaml`:

```yaml
connector_id: bookmarks
paradigm: keyword
freshness: live
privacy_tier: private_local
query_leaks_externally: false
scope: >
  The user's saved web bookmarks (title, URL, notes), searched by keyword.
  Read from a local JSON file at query time.
```

`scope` is documentation only. The planner never reads it, so describing
the source there has no effect on routing.

## 2. Implement the connector

The class must match the `Connector` protocol in
`src/capretrieve/contracts/protocol.py`. It's a structural protocol, so no
base class is needed.

`src/capretrieve/connectors/bookmarks/connector.py` (plus an empty
`__init__.py` in that folder):

```python
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.manifest.models import CapabilityManifest


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


class BookmarksConnector:
    def __init__(self, manifest: CapabilityManifest, path: Path) -> None:
        self._manifest = manifest
        self._path = path

    def manifest(self) -> CapabilityManifest:
        return self._manifest

    async def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        # File and network I/O is blocking: keep it off the event loop.
        bookmarks = await asyncio.to_thread(self._load)
        query = _words(req.query)
        scored = []
        for b in bookmarks:
            text = f"{b['title']} {b.get('notes', '')}"
            hits = len(query & _words(text))
            if hits:
                scored.append((hits, b, text))
        scored.sort(key=lambda item: -item[0])
        now = datetime.now(timezone.utc)
        return RetrievalResult(
            evidence=[
                Evidence(
                    source_id=self._manifest.connector_id,
                    content=text,
                    score=float(hits),
                    uri=b["url"],
                    retrieved_at=now,
                )
                for hits, b, text in scored[: req.top_k]
            ]
        )

    async def health(self) -> HealthStatus:
        if not self._path.exists():
            return HealthStatus(state=HealthState.DOWN, detail=f"{self._path} not found")
        return HealthStatus(state=HealthState.OK)

    def _load(self) -> list[dict]:
        return json.loads(self._path.read_text(encoding="utf-8"))
```

Rules every connector must follow:

- **Take the manifest as a constructor argument.** Don't build it in code.
  The registry rejects a connector whose `manifest()` differs from its YAML.
- **`source_id` must be the `connector_id`.** Fusion and citations use it
  for provenance.
- **`score` is native to your source; higher means more relevant.** Fusion
  normalises each source's scores separately, so any scale works.
- **Set `uri`** to something a person can follow: a URL, a file path, a note
  name. Synthesis cites it.
- **Return at most `req.top_k` items.**
- **Ignore `req.filters` you don't understand.** Today the only filter is
  `{"seed_note": ..., "depth": 1}`, sent for relational queries, and those
  only reach `graph_traversal` sources.
- **Run blocking calls with `asyncio.to_thread`.** A blocking call inside
  `retrieve` stalls every other request on the server.
- **Raising is allowed.** A failed `retrieve` is recorded in the trace for
  that source, and the query continues with the others.
- **Don't add routing logic.** The connector never decides whether it
  should be used; the manifest and planner do.

## 3. Register it

Add it to `build_default_registry()` in `src/capretrieve/bootstrap.py`:

```python
from capretrieve.connectors.bookmarks.connector import BookmarksConnector

    bookmarks = BookmarksConnector(
        manifest=manifests["bookmarks"], path=settings.bookmarks_path
    )
    registry.register(bookmarks)
```

If it needs configuration (a path, an API key), add a field to `Settings`
in `src/capretrieve/settings.py` using the `_env()` helper, and document it
in `.env.example`:

```python
    bookmarks_path: Path = field(
        default_factory=lambda: Path(
            _env("BOOKMARKS_PATH", str(REPO_ROOT / "fixtures" / "data" / "bookmarks.json"))
        )
    )
```

**Every manifest in `configs/connectors/` needs a registered connector.**
The planner considers every manifest, and a request that selects one with
no connector fails.

## 4. Update the tests

| What                                   | Where                                                                                                   |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Unit tests for your connector          | New file in `tests/connectors/`, using `tmp_path` data (see `test_obsidian_connector.py` for the pattern) |
| Connector id sets that list all sources | `tests/connectors/test_contract_conformance.py`, `tests/unit/test_bootstrap.py`, `tests/integration/test_api.py` (search for `{"obsidian", "chroma", "web_search"}`) |
| A smoke query that matches your data   | `SMOKE_QUERIES` in `tests/connectors/test_contract_conformance.py`                                      |
| Registration in test registries        | The `wired_registry` fixtures in `test_contract_conformance.py` and `tests/integration/test_graph_pipeline.py` |
| Aliases people use for the source      | `KNOWN_ALIASES` in `tests/architecture/test_analyzer_isolation.py`, e.g. `"bookmark"`. The test already checks the prompt for your `connector_id` automatically. |

Then run the whole suite. The scenario tests matter most:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/scenarios
```

A new source can change existing plans. In this example, `bookmarks` is
`private_local`, so every question about the user's own notes now also
force-includes it. If a scenario in `fixtures/scenarios.yaml` should now
exclude or include the new source, add it there with the reason.

## 5. Check the routing

Restart the server and confirm:

- `GET /connectors` lists the new manifest.
- `GET /health` reports the new source.
- `/demo`: ask a question that should reach it, and one that must not. The
  Source decisions table shows its score, or the exact rule that blocked it.

For a measured check, re-run the evaluation (see
[evaluation.md](evaluation.md)). The `replay` step re-plans every logged
run offline, so you can see how the new manifest changes each scenario
without new LLM calls.

## What you never need to touch

| Module                                             | Why                                                                                            |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `planner/`                                         | It routes on manifest fields. Your source is just one more manifest.                           |
| `planner/prompts/requirement_extraction.md`        | The analyzer must stay blind to which sources exist. Naming your source there fails a test.    |
| `graph/`, `fusion/`, `generation/`, `trace/`, `api/` | They work with any `Connector` and any `Evidence`.                                           |

The exception is a capability the schema can't express yet, such as a new
paradigm or a remote-but-private tier. That needs a schema change; see
"Changing behaviour" in [manifest-schema.md](manifest-schema.md).
