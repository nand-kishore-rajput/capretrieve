# Positioning: why CapRetrieve exists

## The problem

A retrieval-augmented system with several knowledge sources makes its most
consequential decision before any retrieval happens: where the query goes.
Get it wrong and the system can:

- send private information to a third party (a web search API),
- answer from stale data when the question needs current information,
- miss relationships that only a link-following search would find,
- query sources that add cost and exposure but nothing useful.

Take *"Search the web for advice on my divorce settlement and custody
arrangement."* On the surface it asks for the web. Its content is
confidential, so the web is the one source it must not reach.

## The gap: tool calling standardises invocation, not selection

Today's frameworks describe sources to an LLM in prose and let it choose.
That is the pattern behind LlamaIndex's `RouterQueryEngine` and MCP tool
calling:

| Property         | LLM picks from tool descriptions                                      | CapRetrieve                                                      |
| ---------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Capabilities     | Free text (typed hints such as MCP annotations are optional, unenforced) | Typed manifest: enums and booleans only                        |
| Who decides      | The LLM, by judgement                                                 | A deterministic planner, by rules                                |
| Constraints      | A prompt asking the model to behave                                   | A hard filter the selection step cannot override                 |
| Audit            | Whatever the model says about its choice                              | A trace with every candidate's decision, score and block reason  |
| Changing routing | Rewrite prompts and descriptions, hope                                | Edit a manifest field; the plan changes with no code change (tested) |

## The core idea

> Don't ask the LLM to choose the source. Ask it what the query needs.

CapRetrieve uses the LLM for what it is good at, understanding language, and
takes source selection away from it:

1. **Analyzer (LLM, source-blind).** Turns the query into
   `QueryRequirements`: `privacy_sensitivity`, `needs_freshness`,
   `paradigm_hint`, `relational`, `expects_personal_knowledge`,
   `seed_entity`. The analyzer's prompt names no source. An architecture test
   enforces this, because a prompt that mentions sources would let tool
   picking back in under another name.
2. **Capability manifests (configuration).** Each source declares
   `paradigm`, `freshness`, `privacy_tier` and `query_leaks_externally` in
   YAML. A free-text `scope` field exists for humans and is never read by
   the planner (also enforced).
3. **Planner (deterministic).** Filter, then score, then select. A blocked
   source cannot come back through a high score or a force-include rule.
4. **Trace.** Requirements, per-source decisions, execution results,
   evidence and answer for every query.

The exact rules are in [manifest-schema.md](manifest-schema.md).

## What the evaluation showed

These results come from the evaluation run presented in the project deck.
All LLM calls used `openai/gpt-oss-120b` via Groq. CapRetrieve was compared
with three baselines on the ten scenarios in `fixtures/scenarios.yaml`:

- **keyword**: TF-IDF match of the query against each source's `scope` text.
- **tool_description**: an LLM picks sources from their names and `scope`
  text (the `RouterQueryEngine` / MCP pattern).
- **tool_description_policy**: the same, with CapRetrieve's privacy rule
  stated in the prompt. This is the strongest prose-based baseline.

LLM-based routers ran 10 times per scenario; the keyword router ran once.
Eight scenarios are scored. S2 and S3 are known gaps (see
[future-work.md](future-work.md)). S6 to S10 were written after the analyzer
prompt, scoring weights and threshold were frozen.

**Routing accuracy.** CapRetrieve selected the correct sources in **95%** of
its 80 scored runs (76/80), the highest of the four routers. On the held-out
scenarios S6 to S10 it scored **98%** (49/50). The per-router breakdown is in
the generated `src/capretrieve/evaluation/reports/<batch>_summary.md`.

**Privacy.** Web selections on the privacy-sensitive scenarios (S1, S6, S7, S8):

| Router                  | Runs sent to the web |
| ----------------------- | -------------------- |
| **CapRetrieve**         | **0 / 40**           |
| keyword                 | 2 / 4                |
| tool_description        | 40 / 40              |
| tool_description_policy | 13 / 40              |

Of CapRetrieve's 40 privacy-sensitive runs, 32 were blocked by the privacy
rule. The other 8 stayed off the web because of scoring, after the analyzer
failed to flag them. The prompted privacy rule cut web leaks from 40 to 13,
but it was not equivalent to an enforced one.

**Ablation (replayed offline from the logged analyzer outputs).** Removing a
single field shows that the declared capabilities do the work:

| Removed field                         | Accuracy       |
| ------------------------------------- | -------------- |
| none (full system)                    | 95% (76/80)    |
| `query_leaks_externally` (manifest)   | 62% (50/80), 26 privacy violations |
| `privacy_sensitivity` (requirements)  | 62% (50/80), same 26 violations    |
| `paradigm`                            | 72% (58/80)    |
| `freshness`                           | 82% (66/80)    |
| `relational`                          | 84% (67/80)    |

Accuracy was identical for every selection threshold from 0.1 to 0.9, so the
95% does not depend on tuning that value.

**Where the remaining errors come from.** The planner is deterministic.
Given the same requirements and manifests it always produces the same plan.
All routing variance comes from the analyzer. Examples: S7 was rated "not
private" in 8 of 10 runs, and `needs_freshness` varied on S1.

The raw logs and summaries are written to `src/capretrieve/evaluation/reports/`
(gitignored). To reproduce (details in [evaluation.md](evaluation.md)):

```bash
python -m capretrieve.evaluation.runner --runs 10 --batch-id main
python -m capretrieve.evaluation.compare --batch-id main
python -m capretrieve.evaluation.replay --batch-id main
```

The evaluation measures routing only, not answer quality.

## What it does and does not guarantee

**It does guarantee:**

- Given the requirements, routing follows explicit rules over typed
  capabilities, and the same input always gives the same plan.
- A source blocked by a hard constraint is never queried.
- Every candidate's decision and block reason is recorded and explainable.
- Editing a manifest changes routing with no code change (tested in
  `tests/scenarios/test_manifest_sensitivity.py`).

**It does not guarantee:**

- **Correct requirements.** Privacy protection works only if the analyzer
  flags the query as sensitive. A query the analyzer misreads is routed as
  the analyzer described it.
- **That the LLM calls stay local.** The analyzer and synthesis calls go to
  an external provider unless `LLM_API_BASE` points at a local model. The
  query text, and the retrieved notes, leave the machine for those calls.
- **Content coverage.** A source can have the right capability and still not
  contain the answer.
- **Broad generality.** The evaluation used one model, one vault, one corpus
  and ten adversarial scenarios.

## Who it is for

- Builders of multi-source RAG systems who need source selection they can
  explain and enforce: privacy rules that hold, decisions an auditor can
  read.
- Researchers comparing structured routing with LLM tool selection. The
  baselines and replay tooling in `src/capretrieve/evaluation/` are built for
  that comparison.
