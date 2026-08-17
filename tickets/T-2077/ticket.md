---
id: T-2077
title: 'ARCH001: split _file_regression_ticket and run_deferred_post_land_sweep in
  _rapid_sweep.py'
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: new tests added for the ARCH001 split's extracted helpers
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestRegressionCountLine::test_true_count_known
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
- tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline
designated_repro_test: null
acceptance:
- text: ARCH001 absent for src/frob/app/ticket_runner/_rapid_sweep.py in frob check
    --only archgate
  evidence:
  - tests/unit/test_rapid_sweep.py::TestRegressionCountLine::test_true_count_known
  - tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before
  - tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two functions exceed ARCH001's 60-line threshold: _file_regression_ticket (174 lines, line 1000) and run_deferred_post_land_sweep (125 lines, line 1742). Split into smaller helpers without behavior change. No-behavior-change refactor.

## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_regression_count_line (new, private)
- src/frob/app/ticket_runner/_rapid_sweep.py::_build_regression_body (new, private)
- src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket (split, no behavior change)
- src/frob/app/ticket_runner/_rapid_sweep.py::_close_and_log_resolved_sweep_tickets (new, private)
- src/frob/app/ticket_runner/_rapid_sweep.py::_resolve_regression_attribution (new, private)
- src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep (split, no behavior change)
- tests/unit/test_rapid_sweep.py: added TestRegressionCountLine, TestBuildRegressionBody

frob:no-behavior-change -- both split functions now delegate to the new
private helpers; every branch/condition/log line/return value is
unchanged. `run_deferred_post_land_sweep`'s call to `_file_regression_
ticket` deliberately keeps the original conditional shape (attributed_ids
kwarg only passed when not None) rather than always passing it, to match
the pre-existing test double's exact call signature and avoid a spurious
API-shape change outside this ticket's stated scope.

T-2034 ledger-write-discipline check (per brief): read both functions'
neighbourhood for any ledger write NOT routed through the T-2034 shared
`_commit_or_discard_ledger_write` helper. Both write paths this file has
(`_commit_regression_ticket` -> the new-ticket write, and
`_maybe_drop_resolved_ticket` -> the auto-drop write) already route
through it -- confirmed by reading the call sites directly, not by
inference. No behavior defect found; nothing filed.

T-1703 swallowed-error check (per brief): `run_deferred_post_land_sweep`
already treats `_unscoped_error_findings(...) is None` as `Err(
RapidSweepError.Unmeasurable)`, never as a clean verdict -- no truncation
silently reads as CLEAN in this function. No behavior defect found;
nothing filed.

Evidence:
- tests/unit/test_rapid_sweep.py::TestRegressionCountLine::test_true_count_known (accepts 0)
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before (accepts 0)
- tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline (accepts 0)
- Full touched-set suite: `pytest tests/unit/test_rapid_sweep.py -q` -> 87 passed, 0 failed (measured twice, post-merge-with-main included)

Filed: none (both structural checks above turned up no separate defect
to file)

Gates (measured, worktree `rapid-sweep-archgate`, post-merge with main
at fd733e484):
- `frob check --only archgate` (unscoped): 0 errors, 0 warnings for
  gate:ARCH -- ARCH001 absent for src/frob/app/ticket_runner/_rapid_sweep.py
  (before: ARCH001 x2 on this file, per the measured floor in the brief)
- `frob check --only gates-fast/gates-native/gates-security --ticket
  T-2077`: gate:SCOPE 0 errors (49 warnings, pre-existing
  under-capture style, not new), gate:COV 1 error (COV001 on
  src/frob/strata/_claims.py, unrelated file never touched by this
  ticket, confirmed pre-existing on main), gate:ARCH 4 errors
  (repo-wide, none in _rapid_sweep.py, confirmed by grep)
- `frob check --land-parity`: FAILS with 2 unscoped errors (COV001 +
  DOC002, both src/frob/strata/_claims.py) -- confirmed pre-existing on
  main (never touched by this ticket, present in `main` before this
  worktree branched); not a regression introduced here. This is the
  repo's known floor, not this ticket's responsibility to clear.
- `git diff main --diff-filter=D --stat`: empty after merging main
  (T-2073/T-2075 files that looked deleted before the merge were only
  new-on-main since this worktree was created)

### Changed
```
 tickets/T-2077/ticket.md | 42 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 42 insertions(+)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRegressionCountLine::test_true_count_known` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_no_attribution_files_everything_as_before` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepRun::test_new_findings_file_a_ticket_and_rebaseline` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV001@src/frob/strata/_claims.py, DOC002@src/frob/strata/_claims.py
