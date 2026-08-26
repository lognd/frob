# frob.ci_report -- structured CI failure reporting

One sentence: `frob.ci_report` turns a `frob.ghio.JobLog`'s raw pytest
output into typed `TestFailure`/`FailureCluster`/`JobReport`/`RunReport`
records, so the operator asks "what is failing" and gets an answer
instead of a log dump to grep by hand.

## Why (T-2982/T-2984)

The measured incident this module exists to close: pulling 156 macOS
failure node ids out of a raw job log by hand, hand-clustering them, and
a ~100-failure cluster mis-attributed as macOS-specific for an entire
investigation because the ubuntu job had been cancelled mid-run and
nothing surfaced that fact.

## Why not positional

This repo's own pytest addopts run `-n auto --dist=loadgroup`: the live
progress stream (`.`/`F` characters) is written in COMPLETION order,
interleaved across worker processes, so a character's position cannot be
mapped back to a test node id. The only sound source of failed node ids
is pytest's own "short test summary info" block and its final result
count line -- both written once, at the very end of a run that actually
reached that point. `parse_pytest_log` never attempts positional
inference.

## The `not_recoverable` outcome

`JobReport.outcome` is one of three values, never collapsed to two:

- `"clean"` -- pytest's own result line reports zero failed/errored.
- `"failures"` -- named `TestFailure` records, taken from the short
  summary block.
- `"not_recoverable"` -- pytest's own result line was never observed in
  this log (the run was cancelled before it got there, a worker died, or
  any other reason execution never reached the end). This is the
  measured cancelled-run case (`JobLog.truncated`) named explicitly
  rather than reported as zero failures, which would read as "clean" to
  anyone who did not separately check `truncated`. A log whose captured
  bytes happen to END on an apparently-clean result line is STILL
  `not_recoverable` when `truncated=True` -- a cancelled run's tail is
  not trusted even when it looks clean.

## Clustering

`_signature` collapses a failure's `(kind, reason)` to a clustering key
with digits/hex/quoted literals stripped, so the same root cause failing
across many parametrized node ids (or platform variants) clusters into
one `FailureCluster` instead of N near-identical entries. Clustering is
always PER JOB -- one `gh` job already corresponds to one CI matrix leg
(e.g. one OS), so a cluster's membership can never again be silently
pooled across platforms the way the motivating incident's hand-clustering
was.

## Data models

- `TestFailure` -- one named `FAILED`/`ERROR` line: `node_id`, `kind`
  (`"failed"` | `"error"`), `reason`, `signature`.
- `FailureCluster` -- every `TestFailure` in one job sharing a
  `signature`: `node_ids`, `sample_reason`.
- `JobReport` -- one job's `outcome`, its `failures` and `clusters`,
  plus `truncated` passed through from `JobLog`.
- `RunReport` -- `run_id`, `conclusion`, and one `JobReport` per job.

## Public API

- `parse_pytest_log(text, *, truncated) -> (outcome, failures)`.
- `build_job_report(root, run_id, job) -> Result[JobReport, GhError]` --
  wraps `frob.ghio.job_log` + `parse_pytest_log`. Propagates a `GhError`
  when the log could not be retrieved at all.
- `build_run_report(root, run_id) -> Result[RunReport, GhError]` --
  wraps `frob.ghio.view_run` + `build_job_report` for every job. A
  single job's log-retrieval failure degrades to a `not_recoverable`
  `JobReport` for that job alone rather than aborting the whole run's
  report; a run-level failure (`view_run` itself erring) propagates as
  `Err`.

## Testing without `gh`

Every test in `tests/test_ci_report.py` fakes at the `frob.ghio`
boundary (`job_log`/`view_run` monkeypatched), the same discipline
`tests/test_ghio.py` uses one layer down -- no test here depends on `gh`
being installed, authenticated, or pointed at a real remote.

## frob:doc coverage

This anchor is the `frob:doc` target for every public symbol in
`src/frob/ci_report.py`; see that file's own `frob:doc`/`frob:tests`
directives for the per-symbol binding this page satisfies.
