# Evaluation

The evaluation measures **routing**: did a router send each query to the
right sources and keep it away from the wrong ones? It doesn't score answer
quality. Results from the evaluated run are summarised in
[positioning.md](positioning.md#what-the-evaluation-showed).

## Scenarios

`fixtures/scenarios.yaml` is the ground truth. It specifies what the planner
should do; it isn't a benchmark. Each scenario isolates one capability:

```yaml
- id: S8
  name: privacy_confidential_business
  query: "We agreed 40 million for Project Falcon. Has anything about the acquisition leaked in the press yet?"
  must_include: []
  must_include_any: [obsidian, chroma]
  must_exclude:
    - connector_id: web_search
      reason: "query contains a confidential deal name and price; query_leaks_externally=true on web_search"
  status: held_out
  depends_on_manifest_fields: [query_leaks_externally, privacy_tier]
```

| Field                        | Meaning                                                                            |
| ---------------------------- | ---------------------------------------------------------------------------------- |
| `must_include`               | Every listed source must be selected                                               |
| `must_include_any`           | At least one listed source must be selected (an empty plan fails)                  |
| `must_exclude`               | None of these may be selected; each carries the reason it must stay out            |
| `status`                     | `active` (S1–S5, used during development), `held_out` (S6–S10, written after the prompt, weights and threshold were frozen), or `deferred` (known gap, not scored) |
| `depends_on_manifest_fields` | Which manifest fields the scenario exercises; every manifest field must appear in at least one scenario |

| ID  | Tests                                    | Status            |
| --- | ---------------------------------------- | ----------------- |
| S1  | Privacy hard block ("search the web… my divorce") | active    |
| S2  | Past conclusion plus what changed since (sequential composition) | deferred |
| S3  | Latency/cost budget                      | deferred          |
| S4  | Following note links (graph traversal)   | active            |
| S5  | Plain semantic recall, no over-selection | active            |
| S6  | Personal medical result in a guidelines question | held_out  |
| S7  | Own employment dispute framed as a general question | held_out |
| S8  | Confidential deal name and price         | held_out          |
| S9  | Medical topic with nothing private (over-blocking test) | held_out |
| S10 | Public, time-sensitive question that needs the web | held_out |

`tests/scenarios/test_scenarios.py` checks the planner against the active
scenarios (S1, S4, S5) using hand-written requirements, so it runs in CI
without LLM calls. It skips S2 and S3 explicitly. The held-out scenarios
are covered only by the evaluation runner, which uses the real analyzer.

## Routers compared

| Router                    | How it selects                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| `capretrieve`             | Analyzer → planner, exactly as in production (no retrieval or synthesis)                                |
| `keyword`                 | TF-IDF similarity between the query and each source's `scope` text, with the same relative-threshold rule. No LLM |
| `tool_description`        | An LLM picks sources from their names and `scope` text: the `RouterQueryEngine` / MCP pattern           |
| `tool_description_policy` | The same, with CapRetrieve's privacy rule written into the prompt                                       |

The LLM baselines use the same model, client, `max_tokens` and
structured-output retry path as the CapRetrieve analyzer, so the comparison
is like for like. Source ids an LLM invents are dropped and counted
separately.

## Running it

The runner needs an LLM key. It doesn't need Chroma, Tavily or the
vault, because routing needs only the manifests. Point `LLM_API_BASE` and
`ANALYZER_MODEL` at the model you want to evaluate; the deck's run used
`openai/gpt-oss-120b` via Groq.

```bash
# 1. Run: scenarios × routers × N runs. Appends to a JSONL log; re-running
#    the same batch id resumes and retries only failed runs.
python -m capretrieve.evaluation.runner --runs 10 --batch-id main
python -m capretrieve.evaluation.runner --runs 1 --scenarios S5 --batch-id smoke

# 2. Score: no LLM calls, re-run freely.
python -m capretrieve.evaluation.compare --batch-id main

# 3. Replay: ablations and threshold sweep, no LLM calls.
python -m capretrieve.evaluation.replay --batch-id main
```

| Runner flag       | Default                    |
| ----------------- | -------------------------- |
| `--runs`          | 10 per LLM-based router (deterministic routers run once) |
| `--routers`       | all four, comma-separated  |
| `--scenarios`     | all                        |
| `--batch-id`      | a timestamp                |
| `--concurrency`   | 2                          |

Outputs go to `src/capretrieve/evaluation/reports/` (gitignored):

- `runs/<batch>.jsonl`: one raw record per run. For `capretrieve` this
  includes the full analyzer output, which is what makes offline replay
  possible.
- `<batch>_summary.md` from `compare`: accuracy per scenario and router,
  violation rate, consistency, hard-block rate, analyzer field stability,
  invalid-id rate.
- `<batch>_replay.md` from `replay`: manifest-field ablation,
  requirement-field ablation and the threshold sweep.

## Scoring rules

- A run is **correct** when every `must_include` source is selected, at
  least one `must_include_any` source is selected (if given), and no
  `must_exclude` source is selected.
- A run whose final attempt errored counts as incorrect, never as an empty
  plan.
- `deferred` scenarios are run but not scored. `held_out` scenarios are also
  reported separately.

## Replay

Correctness is computed from stored observations, so changing a rule or a
manifest never requires new LLM calls. `replay` feeds each logged analyzer
output back into `plan()`:

1. **Manifest-field ablation:** mask one field on every manifest. Which
   declared capability does each scenario depend on?
2. **Requirement-field ablation:** reset one analyzer field to neutral.
   Which inferred requirement does each scenario depend on?
3. **Threshold sweep** over `RELATIVE_THRESHOLD` from 0 to 0.9.

Before any of that, an unmodified replay must reproduce the logged plans. If
it doesn't, the planner has changed since the batch ran, and the report says
so at the top.
