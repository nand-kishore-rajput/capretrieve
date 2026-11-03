# Manifest schema and routing rules

Routing is decided by two typed objects meeting in the planner:

- a **capability manifest** per source: what the source can do, declared in
  `configs/connectors/<id>.yaml`;
- the **query requirements**: what the query needs, produced by the analyzer
  for each query.

The planner reads only the typed fields below. Every rule is listed here
exactly as the code applies it.

## Capability manifest

Model: `CapabilityManifest` in `src/capretrieve/manifest/models.py`.

| Field                    | Type    | Values                                       | Read by                                                                                   |
| ------------------------ | ------- | -------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `connector_id`           | string  | unique id, e.g. `web_search`                 | registry, trace                                                                           |
| `paradigm`               | enum    | `dense_semantic`, `graph_traversal`, `keyword` | paradigm hard rule, paradigm bonus                                                      |
| `freshness`              | enum    | `static`, `index_time`, `live`               | freshness bonus, freshness force-include (only `live` matters)                            |
| `privacy_tier`           | enum    | `private_local`, `public_external`           | personal-knowledge bonus and force-include (only `private_local` matters)                 |
| `query_leaks_externally` | boolean | `true`, `false`                              | privacy hard rule                                                                         |
| `scope`                  | string  | free text                                    | **Never read by the planner.** Documentation for humans, and input to the keyword baseline |

`privacy_tier` and `query_leaks_externally` are separate on purpose. Where
the data lives and whether the query text leaves the machine are independent
facts: a private remote database may not leak the query, while a public
search API always does. Only the leak flag drives the privacy block.

The three manifests shipped in `configs/connectors/`:

| Field                    | `obsidian`        | `chroma`         | `web_search`      |
| ------------------------ | ----------------- | ---------------- | ----------------- |
| `paradigm`               | `graph_traversal` | `dense_semantic` | `keyword`         |
| `freshness`              | `live`            | `index_time`     | `live`            |
| `privacy_tier`           | `private_local`   | `private_local`  | `public_external` |
| `query_leaks_externally` | `false`           | `false`          | `true`            |

Example, `configs/connectors/web_search.yaml`:

```yaml
connector_id: web_search
paradigm: keyword
freshness: live
privacy_tier: public_external
query_leaks_externally: true
scope: >
  Live web search through an external search API. Returns current results
  from the public internet. The query text is sent to a third-party service.
```

The loader (`manifest/loader.py`) validates every file against the model
and fails on an invalid file or a duplicate `connector_id`.

## Query requirements

Model: `QueryRequirements` in `src/capretrieve/planner/models/requirements.py`,
filled by the analyzer from the prompt in
`src/capretrieve/planner/prompts/requirement_extraction.md`.

| Field                        | Type           | Values                                              | Meaning                                                                   |
| ---------------------------- | -------------- | --------------------------------------------------- | ------------------------------------------------------------------------- |
| `paradigm_hint`              | enum           | `dense_semantic`, `graph_traversal`, `keyword`, `unknown` | The retrieval style that best fits the question                     |
| `relational`                 | boolean        |                                                     | The question is about links between items ("what links to X")             |
| `needs_freshness`            | enum           | `any`, `recent`, `live`                             | How current the information must be                                       |
| `privacy_sensitivity`        | enum           | `none`, `personal`, `confidential`                  | Whether the query text itself is sensitive                                |
| `expects_personal_knowledge` | boolean        |                                                     | The question asks about the user's own notes, decisions or history        |
| `seed_entity`                | string or null |                                                     | For relational questions, the item to start from ("project retrospective") |

## The rules

`plan()` in `planner/planner.py` applies three stages to every manifest.

### 1. Hard filter (`planner/constraints.py`)

Checked in this order. The first rule that fires excludes the source and
records the reason. An excluded source is never scored and cannot be
selected.

| Constraint id       | Fires when                                                          | Recorded detail                                                                   |
| ------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `privacy_leak`      | `privacy_sensitivity != none` **and** `query_leaks_externally = true` | `privacy_sensitivity=<value> and query_leaks_externally=true on <connector_id>` |
| `paradigm_mismatch` | `relational = true` **and** `paradigm != graph_traversal`           | `paradigm=<value> cannot satisfy a relational/graph-traversal query`              |

### 2. Soft score (`planner/scoring.py`)

Additive bonuses, declared as constants rather than learned:

| Bonus                            | Value | Applies when                                                    |
| -------------------------------- | ----- | --------------------------------------------------------------- |
| `PARADIGM_MATCH_BONUS`           | 1.0   | `paradigm_hint` equals the manifest's `paradigm` (`unknown` never matches) |
| `PERSONAL_KNOWLEDGE_LOCAL_BONUS` | 0.5   | `expects_personal_knowledge = true` and `privacy_tier = private_local` |
| `FRESHNESS_MATCH_BONUS`          | 0.3   | `needs_freshness` is `recent` or `live` and `freshness = live`  |

### 3. Select (`planner/selection.py`)

Over the admitted sources only:

1. **Force-include personal sources.** If `expects_personal_knowledge`,
   every `private_local` source is selected.
2. **Force-include live sources.** If `needs_freshness` is `recent` or
   `live`, every `live` source is selected.
3. **Relative threshold.** Any other source is selected if its score is at
   least `RELATIVE_THRESHOLD × top score`, with `RELATIVE_THRESHOLD = 0.75`.

Edge cases:

- **Every source blocked:** the plan is empty. This is a valid outcome and
  is reported in the trace.
- **All admitted scores are 0:** the first admitted source in registry
  order is used.
- **Selected order:** by score, highest first, ties broken by
  `connector_id`.

Force-includes never bring back a blocked source. Hard constraints are not
preferences.

## Worked example

*"We agreed 40 million for Project Falcon. Has anything about the
acquisition leaked in the press yet?"* (scenario S8, from a live run with
the Claude Haiku analyzer)

Requirements: `paradigm_hint=keyword`, `relational=false`,
`needs_freshness=live`, `privacy_sensitivity=confidential`,
`expects_personal_knowledge=true`, `seed_entity=null`.

| Source       | Filter                    | Score                                         | Selected?                                                   |
| ------------ | ------------------------- | --------------------------------------------- | ----------------------------------------------------------- |
| `web_search` | **blocked:** `privacy_leak` | not scored                                  | no                                                          |
| `obsidian`   | admitted                  | 0 (paradigm) + 0.5 (personal) + 0.3 (live) = **0.8** | yes, top score                                        |
| `chroma`     | admitted                  | 0 + 0.5 (personal) + 0 = **0.5**              | yes: below 0.75 × 0.8 = 0.6, but force-included as personal |

The web scored best on paradigm (`keyword`) and freshness (`live`), and it
still could not be selected.

## Changing behaviour

**Without code changes.** Edit a manifest field. For example, setting
`query_leaks_externally: true` on `chroma` makes the privacy rule block it
for every sensitive query. `tests/scenarios/test_manifest_sensitivity.py`
checks this property by editing real YAML files.

**With code changes.** Adding a new enum value (a new paradigm, a
`private_remote` tier) or a new field means updating the model, the rule
that should read it, the analyzer prompt if it is a requirement field, and
the tests. The project rule is that every field must be justified by at
least one scenario in `fixtures/scenarios.yaml`: a field that drives no
decision in any scenario does not belong in the schema yet.

Fields that were deliberately removed and are planned to return:
`typical_latency_ms` and `cost_per_call`, for the latency/cost budget
scenario S3 (see [future-work.md](future-work.md)).
