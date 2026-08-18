---
id: T-2330
title: 'Clear DRIFT001/DRIFT002 error floor: rapid_sweep, fmt_directives, fleet_status,
  drain doc/test edges'
state: queued
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
- src/frob/verify/_drain.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given the 5 named DRIFT001/DRIFT002 findings, when each symbol's doc/test
    binding is re-read against its current body, then it is either genuinely re-acked
    (content still true) or the doc/test is fixed first
  evidence: []
- text: given the fix is landed, when frob check --only docblocks --json is re-run,
    then none of the 5 named findings remain
  evidence: []
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
