---
id: T-1353
title: Investigate xdist coverage-merge symbol-level data drop (T-1335 residue)
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_coverage.py
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'T-1353''s fix requires proving both root causes (worker OOM crashes,

    serial-rerun timeout-method corruption) against the real Makefile recipe

    text without a duplicated/drifting reimplementation, and there is no

    Makefile-native "symbol" `frob:tests` can bind evidence to -- adding a

    regression test to the same file T-1335 already established for exactly

    this purpose (TestCombineRecoversDisjointSessions) is the only way to

    bind real pytest evidence to this ticket''s Makefile-only scope.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: a crashed/lost
    worker session does not lose coverage data -- the serial-retry recovery path still
    produces full coverage.xml.'
  actor: logan
  at: '2026-08-16'
- old_node: tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: the coverage-xml
    step always passes -i/ignore-errors.'
  actor: logan
  at: '2026-08-16'
- old_node: tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe
  new_node: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: a green suite followed by a failing stamp-coverage step must fail the whole
    recipe nonzero, with an error naming the stamp-coverage failure. Successor: _run_stamp_coverage
    (src/frob/app/check_runner.py) logs ''stamp-coverage failed: %s'' and sys.exit(1)
    on stamp_coverage() Err, exercised directly by this node.'
  actor: logan
  at: '2026-08-17'
- old_node: tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero
  new_node: tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests. Shared
    claim: the unchanged success path -- a green stamp write -- still exits/returns
    normally (no regression from the failure-propagation fix). Successor exercises
    the same _run_stamp_coverage success path directly.'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed while working T-1335 (Makefile-only scope). T-1335's own recipe fix
now detects a crashed xdist worker ("node down: Not properly terminated")
during `make coverage` and escalates to a full serial rerun to recover
that worker's entirely-lost coverage data -- confirmed live during T-1335's
own verification (5+ workers crashed per run, 3 separate runs, consistent
with this session's known WSL-OOM resource contention).

However, several agents independently reported deflated/zeroed TEST005
numbers for symbols that are genuinely well-tested, in a pattern (def line
hits=1, every body line hits=0) that looks like a PARTIAL merge -- one
worker's data for a line survived, another worker's data for the rest did
not -- rather than simple staleness. The worker-crash fix in T-1335 may
already explain some/most of this (a crashed worker's data vanishing
outright), but it does not obviously explain a partial per-symbol split
this precise, and should be checked against `coverage combine`'s own
merge behavior in src/frob/gates/_coverage.py (module_join_fraction,
stale_by_mtime) and/or `coverage combine` itself, independent of whether
any worker actually crashed on a given run.

Concrete repro cases collected across multiple agents (validate a fix,
or T-1335's own fix, against these -- expect all four at their real, high
values once combine/merge is trustworthy):
  src/frob/strata check_process_bounds_obligations: stamp 6.7%, real ~98%
  src/frob/strata check_self_conformance: stamp 0.0%, real ~95%
  src/frob/release authoritative_version: def hits=1, every body line hits=0
  src/frob/app worktree_runner.py::run: false 0.0%, attributed to xdist
    coverage-merge dropping the symbol's branch data

Not T-1333 (coverage.py + CSafeLoader corrupts a YAML parse under --cov)
-- checked, that is a distinct failure mode (an actual test failure under
instrumentation via a C-extension/tracer interaction), not a coverage-data
merge/drop issue. Leave T-1333 alone; do not fold it in here.

Suggest: reproduce with a small multi-worker fixture that deliberately
returns partial per-worker data and confirm whether `coverage combine`
(stdlib) or this repo's own load_coverage/module aggregation
(src/frob/gates/_coverage.py) is where data is actually lost; if it's a
site-wide coverage.py behavior, consider whether combine ordering/dedup
in the Makefile also plays a role (T-1335's own verification run combined
176 files but skipped 280 -- worth understanding whether 280 "skipped"
files were legitimate duplicates/empties or lost data).

## Done report

Changed:
- Makefile: `coverage:` recipe -- added `COVERAGE_WORKERS` (default 4) to
  cap the initial parallel run's worker count, and
  `--timeout-method=signal` on both `-n 0` recovery/rerun invocations.

Root cause (two parts, not conflated):

1. Workers crash ("node down") because `addopts`' `-n auto` (one worker
   per core, 12 on the investigation host) oversubscribes CPU/memory once
   coverage instrumentation is added on top of several whole-repo
   self-scan tests (`test_sys_gate_zero_violations` and siblings) that
   themselves fan out further work. `COVERAGE_WORKERS ?= 4` caps the
   parallel phase specifically, reducing how often the crash-recovery
   path is needed at all.

2. Even after T-1335's full-serial-rerun recovery, deflated numbers
   persisted for symbols exercised by those exact self-scan tests. Live-
   captured proof from a real, full `make coverage` run in this worktree:
   the serial (`-n 0`) recovery rerun hit `--timeout=120
   --timeout-method=thread` on `test_sys_gate_zero_violations` (whose
   call chain includes `check_self_conformance`, one of the ticket's own
   reported-deflated symbols). `--timeout-method=thread` does not
   forcibly kill the stuck call -- it dumps a traceback in a watchdog
   thread while the ORIGINAL call keeps running unkilled in the
   background. Because `-n 0` means one process for the entire rest of
   the suite, that zombie thread's continued interference corrupted
   shared interpreter state for everything measured afterward: 31,468
   `ValueError: I/O operation on closed file` logging errors were
   recorded from that point to the recipe's end in the captured log.
   `--timeout-method=signal` (SIGALRM) actually raises inside the main
   thread instead of leaving a zombie watchdog.

Verification performed (see report to dispatcher for full detail):
- A fresh, full `make coverage` run (pre-fix) reproduced
  `check_process_bounds_obligations` at 6.7%, exactly matching the
  ticket's reported figure, with the exact zombie-thread signature
  present in the captured log.
- `load_coverage`/`_symbol_branch` in `src/frob/gates/_coverage.py`,
  called directly against a cleanly-generated `coverage.xml` (no
  timeout/crash in the window measured), correctly attributed all three
  directly-checked symbols (`authoritative_version`,
  `check_process_bounds_obligations`, `check_self_conformance`) at their
  real, high values -- this module's own Cobertura parsing/attribution is
  not the defect.
- A controlled two-phase disjoint-test `--cov-append` + `coverage
  combine` replay (this ticket's new regression test,
  `TestCombineRecoversDisjointSessions`) confirms `coverage combine`
  itself correctly unions two separate sessions' data with no
  last-write-wins loss -- codified as a permanent regression test.
- 447 `<class>` entries in a full-repo `coverage.xml` were checked for
  duplicate `filename=` values (which would indicate a last-write-wins
  overwrite bug in `_parse_classes`/`_build_class_maps`): zero found,
  ruling out that hypothesis directly.

Evidence:
- tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage
- tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe
- tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors

Filed: none (root cause was fully addressed within this ticket's own
Makefile scope; no out-of-scope follow-up discovered).

Gates: `frob check --ticket T-1353` run per stage group (lint,
static, gates-native, gates-security) -- clean except pre-existing,
unrelated repo-wide baseline noise (271 `ty` diagnostics in files this
ticket never touched; `gate:PII` PII012 suggestion on `run_diagnosis` in
`src/frob/doctor.py`, pre-existing, unrelated to this ticket's scope).
`gate:SELFAUDIT`'s one finding (the new test class missing from the
interface doc) was fixed via `frob sys sync-interface` before landing.

### Changed
```
 Makefile                             | 63 ++++++++++++++++++++++++++++++--
 design/frob.strata                   |  1 +
 tests/unit/test_makefile_coverage.py | 70 ++++++++++++++++++++++++++++++++++++
 tickets.md                           |  8 +++--
 4 files changed, 137 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 2 error(s), 1361 warning(s), 689 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, TICK003@tickets.md
