---
id: T-3152
title: fleet_status and frob.process._reap use different age heuristics for the same
  forkserver (mtime vs stat starttime)
state: done
kind: bug
origin: human
created: '2026-08-27'
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
- src/frob/process/_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_process_reap.py::TestProcessStartAge::test_reads_age_from_starttime
- tests/unit/test_process_reap.py::TestProcessStartAge::test_missing_entry_returns_none
- tests/unit/test_process_reap.py::TestProcessStartAge::test_unknown_uptime_returns_none
- tests/unit/test_process_reap.py::TestProcessStartAge::test_zero_clk_tck_returns_none
- tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus::test_same_stat_line_and_uptime_yield_the_same_age
- tests/unit/test_process_reap.py::TestProcessStartAgeMatchesFleetStatus::test_both_agree_none_on_unknown_uptime
- tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_terminates_old_orphaned_forkservers
- tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_leaves_young_orphaned_forkservers_alone
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3139: frob.process._reap._process_start_age_s derives a forkserver's age from the <proc>/<pid> DIRECTORY's own mtime; scripts/fleet_status.py::_forkserver_age_s derives it from /proc/<pid>/stat's starttime field plus /proc/uptime. Both approximate the same quantity and currently agree in practice, but they are not provably identical (a /proc entry's mtime is not guaranteed to equal process start time in every kernel/container scenario) and are a second, independent copy of the same measurement, the exact class of duplication T-3072/T-3093/T-3139 already found three other instances of in this file pair. Unify on one heuristic (prefer stat-starttime, the more precise of the two) or add a cross-check test proving the two never diverge by more than a small epsilon.