# 0004: Adversarial scenarios and baselines, not a public benchmark

**Status:** accepted

## Context

Public RAG benchmarks score answer quality over a single source. The claim
here is narrower: structured routing chooses the right sources, and keeps
sensitive queries away from sources that leak them, more reliably than
letting an LLM choose from descriptions. No existing benchmark measures
that across private notes, a local corpus and the web.

## Decision

- `fixtures/scenarios.yaml` specifies expected behaviour. Each scenario
  isolates one capability, states `must_include` / `must_exclude` with a
  reason for every exclusion, and lists the manifest fields it depends on.
- CapRetrieve is compared with three baselines on the same scenarios
  (`src/capretrieve/evaluation/baselines/`): keyword matching on
  descriptions, an LLM choosing from descriptions, and the same LLM with
  the privacy rule written into its prompt. The LLM baselines share the
  analyzer's model, client and retry path.
- Scenarios S6 to S10 were written after the analyzer prompt, weights and
  threshold were frozen, and are reported separately.
- The evaluation scores routing only, not answer quality.

## Consequences

- Results answer the specific question (does structured routing select
  correctly, and does it hold privacy rules) rather than general RAG
  quality.
- The evaluation set is small: one model, one vault, one corpus, ten
  scenarios. This is stated as a limitation in
  [positioning.md](../positioning.md).
- Runs are logged with the full analyzer output, so ablations and threshold
  sweeps replay offline without new LLM calls (see
  [evaluation.md](../evaluation.md)).
