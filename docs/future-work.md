# Future work and known limitations

Each item comes from a limitation found in the evaluation or while running
the system.

## Planned extensions

### Sequential composition (scenario S2)
*"What did I conclude about switching to a standing desk, and has anything
changed since?"* needs one retrieval to feed the next: find the past
conclusion locally, then use it to shape a web query. The graph only does
parallel fan-out today. S2 is in `fixtures/scenarios.yaml` as `deferred`.

### Latency and cost as typed fields (scenario S3)
Add `typical_latency_ms` and `cost_per_call` back to the manifest, accept a
caller budget, and propagate deadlines through the planner, so that *"quickly
check…"* drops a source that is too slow and flags lower confidence in the
trace. `RetrievalRequest.deadline_ms` already exists but isn't enforced.

### Per-subquery privacy
Sensitivity is judged for the whole query, so a mixed question (*"given my
HbA1c of 7.2, what are this year's new guidelines?"*) keeps everything off
the web. Splitting the query would let the private part stay local while
the public part still uses the web.

### Re-planning on connector failure
A failed source is recorded and skipped today. The next step is to re-run
the match over the remaining manifests, so a fallback source with the
needed capability is chosen instead. `Connector.health()` exists for this
but the planner doesn't consult it yet.

### Local analyzer and synthesis
Both LLM calls currently go to an external provider, so the query text and
the retrieved notes leave the machine even when retrieval stays local.
`LLM_API_BASE` already accepts any OpenAI-compatible endpoint. Running both
calls on a local model would put them inside the same privacy boundary as
the local sources.

### Content-coverage metadata
A source can have the right capability and still not contain the answer. A
typed signal for what a source covers could feed the soft score. It must
never become a hard rule, or free text would creep back into routing.

### More connectors
- **PostgreSQL**, as proof of extensibility. The expectation is that it
  needs a manifest and one connector class, and no planner change (see
  [adding-a-connector.md](adding-a-connector.md)).
- **MCP servers**, wrapped through a manifest sidecar so an existing MCP
  tool gets typed capabilities without changing the server.

### Learned weights and capabilities
The scoring bonuses (1.0, 0.5, 0.3) and the threshold are declared by hand.
With usage logs, they could be learned, along with capability values
themselves.

## Known issues found in testing

### Live sources are force-included for every recent or live query
Obsidian declares `freshness: live`, so any query needing recent information
also selects the personal vault, even a purely public question like S10
(EU AI Act updates). This follows the rules as written, but it adds an
unneeded source and sends personal notes to the synthesis model.

### S1 expects the vault, and the planner doesn't select it
S1 ("search the web… my divorce settlement") lists `obsidian` in
`must_include`. The analyzer consistently reads the query as confidential
but not as asking about the user's own notes, and the vault is
force-included only when `expects_personal_knowledge` is true or the query
needs fresh data. In local test runs with free OpenRouter models, Claude
Opus and Claude Haiku as the analyzer, S1 selected only `chroma` in 4 of 6
runs, and the evaluation deck also reports S1 misses. Either the scenario's expectation
or the selection rule needs to change.

### The relative threshold is currently redundant
The threshold sweep gave identical accuracy for every value from 0.1 to
0.9, because the personal and freshness bonuses fire exactly when a
force-include does. The threshold never changes a plan with the current
weights.

### Analyzer variance is the remaining error source
The planner is deterministic, so every routing error traces back to the
analyzer. Examples from the evaluation: S7 rated "not private" in 8 of 10
runs; one stray `relational=true` on S10 blocked every non-graph source.
Weaker or randomly routed models make this worse. With `openrouter/free`,
S8 (confidential deal) reached the web in 3 of 3 runs. With Claude Haiku as
the analyzer, it was blocked.

### Retrieval and fusion
- **Fusion normalises scores per source with min-max.** Each source's best
  item always becomes 1.0 and its worst 0.0, even when the best is weak.
  Reciprocal Rank Fusion is the more robust standard choice.
- **Chroma stores whole files as single documents.** No chunking, deleted
  files are never removed from the collection, and `a.md` and `a.txt` would
  collide on id.

### Project gaps
- `Makefile` and the four files in `scripts/` are empty placeholders.
- `tests/architecture/test_nodes_are_thin.py` is empty, so the thin-nodes
  rule is checked only in review.
- The `.chroma/` index binaries are committed even though they are build
  output.
