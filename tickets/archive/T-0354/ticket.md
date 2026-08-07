---
id: T-0354
title: app/ticket_runner.py _run_sweep has same full-root xref bug as sweep_ticket
  (T-0240 sibling)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_foreground_runs_sweep_synchronously
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_spawns_detached_sweep_subprocess
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_popen_failure_falls_back_to_synchronous_sweep
- tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep::test_exec_kill_switch_forces_synchronous_sweep
designated_repro_test: null
threat: null
component: null
---
found while working T-0240: gates/_prework.py::sweep_ticket's xref loop called xref(symbol, root) instead of the scan_path it computed, and derived xref-hit terms via Path(pattern).stem (nonsense for glob patterns). app/ticket_runner.py's _run_sweep + _xref_hits_for_scope + _scope_digest_for_ticket carry an IDENTICAL copy of the same loop (already flagged as duplicate call-site debt in T-0236's Done report, follow-up ticket not yet filed) with the same two bugs. src/frob/app/** was out of scope for T-0240 (whose scope was tickets/gates/dup/tests only), so this sibling copy still has the unbounded-walk + nonsense-stem bugs. Either delegate _run_sweep to frob.gates._prework.sweep_ticket directly (collapsing the duplication per T-0236) or port the same fix.