## Done report

Land latency, not startup or graph build, was the throughput ceiling. A
measured land spent ~5 minutes in one place: the synchronous post-land
unscoped `frob check`, plus the T-1463 baseline snapshot check joined
just before it. Two full-repo checks on the critical path of every land.

Under `rapid` those are now zero foreground checks. `_land_core_start_
baseline` starts no thread; `_land_core_finish_post_land` hands the sweep
to a detached `frob ticket sweep-async` child and returns. The child
diffs against a ROLLING baseline (`.frob/rapid-sweep-baseline.json`, the
previous sweep's absolute error set) so the whole verification costs one
background check instead of two foreground ones, and it FILES a bug
ticket for new `(rule, file)` pairs rather than reverting a commit other
agents may already have branched from.

The bargain stays honest: `record_rapid_debt` writes the deferral line
BEFORE the spawn, so "this commit landed unverified" is a machine-
readable fact even if the child never starts. An absent baseline is
`None`, never an empty set -- otherwise the first sweep would report
every pre-existing error as a regression. An unmeasurable check leaves
the baseline untouched. Every sweep, red or green, rebaselines, so an
already-filed error is not re-filed by the next land.

Two root causes were fixed rather than waived on the way:

- WIRE001 fired on `_sweep_async` because a dict-table dispatch entry
  (`"sweep-async": _sweep_async,`) is a by-reference wiring the gate's
  text scan did not recognise -- the same shape it already understood for
  wrapper markers and `_ProcessJob` job tables. Every `frob ticket <verb>`
  handler is wired exactly this way, so waiving would have institutional-
  ised a false-positive class. `_wire_reach_patterns` now matches it.
- `record_rapid_debt` recorded `commit=""` whenever `git rev-parse`
  exited nonzero: `run_argv` signals a SPAWN failure via `Err`, not a
  nonzero exit, and the `is_ok`-only check could not tell those apart.
  An empty string reads as a real value to anything draining the debt
  file. Extracted as `_head_commit_or_unknown`, with a test.

Also closed the T-1681 documentation/test debt this touched: both
`ratchet_override_enabled` and `record_rapid_debt` were public with no
doc anchor and no unit test, and now have a `tickets.md` section plus
covering tests.

Residual errors at land time (3) are all pre-existing on main and
untouched by this diff: a `ty` unresolved-attribute in
test_ticket_work_and_land_finish.py:794, ARCH001 on
`_done_transition_structural_guard`, and DOC009 on a 2026-08-06 audit
file missing its status header.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_unmeasurable_check_leaves_the_baseline_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn::test_exec_disabled_records_debt_and_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_debt.py::TestRecordRapidDebt::test_records_a_commit_field_even_outside_a_git_repo` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile.py::TestRatchetOverride::test_explicit_true_overrides` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 827 warning(s), 721 waived
- error-findings: none (measured, zero errors)
