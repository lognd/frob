---
id: T-2330
title: 'Clear DRIFT001/DRIFT002 error floor: rapid_sweep, fmt_directives, fleet_status,
  drain doc/test edges'
state: done
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/gates/_fmt_directives.py
- scripts/fleet_status.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/verify/_drain.py
  reason: T-2324 holds a live lease on this file; will re-add and land separately
    once free
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: DRIFT002 finding involves scripts/fleet_status.py::_land_status_lines's
    test binding, doc lives in this file's tree
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_no_live_holder_as_normal_resting_state_not_stale
designated_repro_test: null
acceptance:
- text: given the 4 named DRIFT001/DRIFT002 findings (rapid_sweep, fmt_directives
    x2, fleet_status), when each symbol's doc/test binding is re-read against its
    current body, then it is either genuinely re-acked (content still true) or the
    doc/test is fixed first; the 5th (drain) is deliberately out of scope, filed as
    a blocked follow-up
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_no_live_holder_as_normal_resting_state_not_stale
- text: given the fix is landed, when frob check --only docblocks --json is re-run,
    then none of the 4 addressed findings remain (the 5th, drain, is tracked separately,
    blocked by T-2324)
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_no_live_holder_as_normal_resting_state_not_stale
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the 5 named DRIFT001/DRIFT002 findings, when each symbol's doc/test
    binding is re-read against its current body, then it is either genuinely re-acked
    (content still true) or the doc/test is fixed first
  new_text: given the 4 named DRIFT001/DRIFT002 findings (rapid_sweep, fmt_directives
    x2, fleet_status), when each symbol's doc/test binding is re-read against its
    current body, then it is either genuinely re-acked (content still true) or the
    doc/test is fixed first; the 5th (drain) is deliberately out of scope, filed as
    a blocked follow-up
  reason: 'Narrowed to the 4 findings this ticket actually addresses. The 5th

    (DRIFT002 src/frob/verify/_drain.py::run_drain_async) was investigated

    and deliberately left untouched: the file is under T-2324''s live lease

    and the stale test name concerns the exact watermark-advance bug T-2324

    is actively fixing -- repointing it now would either collide with or be

    immediately invalidated by that in-flight work. Filed as a disclosed

    follow-up, blocked_by T-2324, rather than forced into this ticket''s

    scope.

    '
  actor: logan
  at: '2026-08-17'
- op: replace
  index: 1
  old_text: given the fix is landed, when frob check --only docblocks --json is re-run,
    then none of the 5 named findings remain
  new_text: given the fix is landed, when frob check --only docblocks --json is re-run,
    then none of the 4 addressed findings remain (the 5th, drain, is tracked separately,
    blocked by T-2324)
  reason: 'Narrowed to the 4 findings this ticket actually addresses. The 5th

    (DRIFT002 src/frob/verify/_drain.py::run_drain_async) was investigated

    and deliberately left untouched: the file is under T-2324''s live lease

    and the stale test name concerns the exact watermark-advance bug T-2324

    is actively fixing -- repointing it now would either collide with or be

    immediately invalidated by that in-flight work. Filed as a disclosed

    follow-up, blocked_by T-2324, rather than forced into this ticket''s

    scope.

    '
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Live ERROR floor on main, surfaced by `uv run frob check --only docblocks
--json | python3 scripts/check_summary.py` (5 errors after the
coordinator's own CLAUDE001 fix landed the remaining 2 of the original 7
away).

All five are doc/test edges whose digests moved as fresh fallout from
today's lands (T-2312's function split, T-2298's fmt work, T-2126's
fleet_status addition, T-2310's drain change):

 - DRIFT001 src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket (body), 1 dependent
 - DRIFT001 src/frob/gates/_fmt_directives.py::_format_one_path (body), 2 dependents
 - DRIFT001 src/frob/gates/_fmt_directives.py::_format_one_path (sig), 2 dependents
 - DRIFT002 scripts/fleet_status.py::_land_status_lines -> tests/unit/test_coordinator_scripts.py::TestPrintLandStatus...
 - DRIFT002 src/frob/verify/_drain.py::run_drain_async -> tests/unit/verify/test_drain.py::TestRunDrainAsync...

REQUIRED: for each finding, actually read the current symbol body and
the doc/test it is bound to -- do not mechanically `frob ack`/re-bind.
If the doc/test still accurately describes the changed symbol, ack it
(a genuine re-verification, not a rubber stamp). If the doc is now
wrong, or the test edge no longer resolves to a real covering test,
fix the doc or repoint the `frob:tests` edge to a real one, then ack.