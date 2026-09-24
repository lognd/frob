<!-- frob:waive REF002 reason="frob.ci_report is a single, small support module (typed pytest-output parsing) with exactly one consumer by design (src/frob/ci_report.py); a second consumer would not be genuine" -->
<!-- frob:waive INV003 reason="spot-checked against src/frob/ci_report.py::parse_pytest_log: it only ever reads _RESULT_LINE/_SUMMARY_LINE regex matches from the log tail, no positional inference anywhere in the function -- the 'only sound source' claim holds against current code; genuine design intent, not yet formalized as a checked INV-### (T-3520)" -->
<!-- frob:waive INV004 reason="spot-checked against src/frob/ci_report.py::parse_pytest_log: it only ever reads _RESULT_LINE/_SUMMARY_LINE regex matches from the log tail, no positional inference anywhere in the function -- the 'only sound source' claim holds against current code; genuine design intent, not yet formalized as a checked INV-### (T-3520)" -->

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

## This repo's own SUITE-RESULT summary (T-5477)

`-n auto --dist=loadgroup` is exactly why vanilla pytest's own
end-of-run summary text (`"=== N failed, M passed in Ts ==="` plus
`"FAILED <nodeid> - <reason>"` lines) is unreliable for THIS repo in the
first place -- and it turns out `tests/conftest.py`'s own
`pytest_sessionfinish` hook already knows this and writes an alternate,
authoritative summary instead: one `SUITE-RESULT: exitstatus=N
collected=N failed=N` line, followed by one `SUITE-RESULT-FAILED:
<nodeid> (failed|error)` line per named failure. `parse_pytest_log` tries
this SUITE-RESULT shape FIRST (`_parse_suite_result_log`); only when no
`SUITE-RESULT:` line exists at all does it fall back to the vanilla-
pytest path unchanged.

Measured gap this closed (T-5477, CI run 35951365410): before this fix,
`parse_pytest_log` matched NEITHER shape against this repo's own real
`gh api .../actions/jobs/<id>/logs` output -- every line there also
carries a leading ISO-8601 timestamp (`2026-09-24T03:43:26.1010000Z `)
that defeats the `^`-anchored vanilla regexes even where literal pytest
text happens to appear (e.g. inside `tests/system/test_scaffold_dx.py`'s
generated-project pytest subprocess output, which is NOT the outer run's
own result and must never be read as one). Net effect: `build_job_report`
returned `"not_recoverable"` for every real completed CI job in this
repo, silently -- the exact false-negative class this module's own
docstring says it exists to prevent. `_SUITE_RESULT_LINE`/
`_SUITE_RESULT_FAILED_LINE` both accept the optional timestamp prefix and
are authoritative over the vanilla path whenever a `SUITE-RESULT:` line
is present at all, so a nested subprocess's own vanilla summary can never
override the outer run's real result.

`tests/fixtures/ci_report/run_35951365410_ubuntu_trimmed.log` is a
trimmed but otherwise real capture proving all 19 of that run's actual
failing node ids are recovered end to end.

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
