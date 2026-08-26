# frob.ci_validity -- CI result validity against the affects graph

One sentence: `frob.ci_validity` classifies each test outcome from a
`frob.ci_report` job/run report as `STILL_VALID`, `STALE`, or `UNKNOWN`
against the CURRENT tree, so a green CI run from N commits ago is never
read as evidence about the tree as it stands today.

## Why (T-2982/T-2985)

A CI run is evidence about ONE commit (`RunSummary.head_sha`). The moment
code changes, some of that evidence goes stale -- but nothing before this
module said WHICH part. This is the highest-leverage piece of the T-2982
epic: it answers "is this failure/pass still true right now" instead of
leaving that inference to whoever is reading the run.

## The three outcomes

- `STILL_VALID` -- no commit since the run's `head_sha` touched a symbol
  reaching this test (directly, or transitively through a
  `frob:uses-contract` chain). The result stands.
- `STALE` -- the test's own symbol was touched directly, OR some touched
  symbol's `affects()` closure names this test. The result is UNMEASURED
  for the current tree -- explicitly never reported as "passing" (or
  "still failing", for a prior failure whose cause may since be fixed).
- `UNKNOWN` -- the test's own symbol could not be resolved in the graph
  snapshot at all, OR a closure walk that did NOT already find a positive
  match was truncated (`affects()`'s own `max_depth`/`max_nodes` bounds).
  A truncated walk under-reports reachability, so a truncated "no match"
  is honestly `UNKNOWN`, never upgraded to `STILL_VALID`.

## Reuse, not a parallel notion of freshness

This module invents no new staleness machinery:

- `frob.gitio.working_diff(root, run_head_sha)` -- the SAME diff
  primitive `frob.gates.affect_drift_gate` (AFFECT001/AFFECT002) already
  uses to find what changed since a commit.
- `frob.graph.affects.affects` -- the SAME `uses-contract` closure walk
  the north-star `affects()` query performs, applied per touched symbol
  to answer "does this touched symbol reach the test" instead of "what
  does this symbol's own change obligate".
- A local `_touched_symrefs` (span-overlap over `Diff.hunks`) matching
  the SAME algorithm `frob.verify._attribution._touched_symrefs` and
  `frob.tickets._land._touched_symrefs_for_intent` already implement --
  duplicated locally per that pair's own established T-2018 precedent
  (a small, stable, span-overlap function lives in each of its natural
  homes rather than being reached through a private cross-package
  import), not a new duplication pattern.

Nothing here is cached or persisted: every call recomputes against
whatever `snapshot`/tree state the caller passes in, matching
`affects()`'s own pure, snapshot-only posture. A CI verdict must never
outlive its validity without saying so (T-2982's own constraint).

## Doctrine match

`frob.verify` already refuses to attribute against a stale baseline
(T-2929), and gate results render `UNRES` rather than `pass` when
unmeasured (T-2891). A CI result whose code changed underneath it gets
the identical treatment here -- `STALE` is a first-class outcome, never
silently rendered as a green tick.

## Error types

- `ValidityError.DiffUnavailable` -- the diff since the run's
  `head_sha` could not be computed at all (an unresolvable sha, a git
  failure). Never the per-test classification's own outcome -- a test
  that cannot be classified reports `Validity.UNKNOWN`, not an `Err`.

## Data models

- `Validity` -- the three string constants (`STILL_VALID`, `STALE`,
  `UNKNOWN`), plain strings rather than a `StrEnum` for byte-stable
  `--json` rendering.
- `TestValidity` -- `node_id`, `status`, `reason` (always populated, so
  a `STALE`/`UNKNOWN` verdict is never left to guess why).
- `JobValidity` -- one job's `TestValidity` list, restricted to the node
  ids that job's `JobReport.failures` actually named.
- `RunValidity` -- one `JobValidity` per job in a `RunReport`.

## Public API

- `classify_test(snapshot, touched, node_id) -> TestValidity`.
- `validity_for_run_head_sha(root, snapshot, run_head_sha, node_ids) ->
  Result[tuple[TestValidity, ...], ValidityError]` -- computes the diff
  once, classifies every id against it. Fails the WHOLE batch on a diff
  failure rather than reporting some ids and omitting others.
- `job_validity(root, snapshot, run_head_sha, job) -> Result[JobValidity, ValidityError]`.
- `run_validity(root, snapshot, run_head_sha, run) -> Result[RunValidity, ValidityError]`.

## Testing

`tests/test_ci_validity.py` follows `tests/test_graph_affects.py`'s own
minimal-`GraphSnapshot`-fixture pattern, plus a monkeypatched
`working_diff` (mirroring `tests/test_ghio.py`'s subprocess-boundary
discipline one layer up). It carries both classifier directions
required by T-2985's own constraint: a must-classify-`STALE` fixture
(a touched symbol's `affects()` closure reaches the test) and a
must-classify-`STILL_VALID` fixture (nothing relevant changed), plus a
genuine truncation fixture proving `UNKNOWN` is reported rather than a
false `STILL_VALID` when a closure walk is capped before it can confirm
no reachability.

## frob:doc coverage

This anchor is the `frob:doc` target for every public symbol in
`src/frob/ci_validity.py`; see that file's own `frob:doc`/`frob:tests`
directives for the per-symbol binding this page satisfies.
