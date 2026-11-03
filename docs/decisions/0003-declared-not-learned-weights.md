# 0003: Declared scoring weights, not learned ones

**Status:** accepted

## Context

After the hard filter, the planner ranks the remaining sources. The ranking
could come from a learned model or from a few hand-set rules. There's no
usage log to learn from, and the goal is a routing decision a person can
read and check.

## Decision

`planner/scoring.py` uses three declared additive bonuses over typed fields:

| Bonus                     | Value |
| ------------------------- | ----- |
| paradigm match            | 1.0   |
| personal question + local source | 0.5 |
| fresh data needed + live source  | 0.3 |

`planner/selection.py` adds force-include rules and a relative threshold of
0.75. All values are constants in code, covered by unit tests.

## Consequences

- Every score in the trace can be recomputed by hand from the requirements
  and manifests (see the worked example in
  [manifest-schema.md](../manifest-schema.md)).
- The evaluation's threshold sweep gave identical accuracy for every
  threshold from 0.1 to 0.9, so results don't hinge on fine-tuning.
  The same sweep shows the threshold is currently redundant with the
  force-include rules.
- Learning the weights, or the capability values themselves, from usage logs
  is listed in [future-work.md](../future-work.md).
