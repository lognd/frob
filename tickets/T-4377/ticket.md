---
id: T-4377
title: fleet_status.py LANDS IN FLIGHT has no per-repo filter, unlike the T-3885-fixed
  ledger-write scan
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- tests/unit/coordinator_suite/test_fleet_land.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/coordinator_suite/test_fleet_land.py
  reason: tests for the T-4377 fix live in this file
  actor: logan
  at: '2026-09-09'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'AFFECT001: new symbols under land_process_rows own affects-closure doc
    anchor'
  actor: logan
  at: '2026-09-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3885: the ledger-write process scan (frob.tickets._leases._scan_for_live_land_process) is correctly repo-scoped (exact cwd match) and now also excludes a land's own ancestor chain (T-3885). scripts/fleet_status.py's own separate implementation (land_process_rows/land_invocations, a machine-wide ps -eo pid,etimes,time,args scan) has NO cwd/repo filter at all -- it will still report a land running in a completely different repository as part of THIS repo's LANDS IN FLIGHT. The original T-3885 ticket explicitly asked for this to be fixed too ('CHECK fleet_status.py TOO... if they duplicate the logic, that duplication is itself worth removing'), but this series scoped tightly to the lock module (src/frob/tickets/_leases.py) per explicit coordinator instruction. Fix: filter land_process_rows/land_invocations by cwd or --worktree-resolved target repo, ideally sharing _leases.py's _live_pids_with_cwd/_process_ancestor_pids primitives (or the T-2691 land-status marker) rather than a second independently-invented predicate.