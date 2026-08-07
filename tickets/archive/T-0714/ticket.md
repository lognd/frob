---
id: T-0714
title: 'ticket doable: relocate stale-lease/scope diagnostics to frob check (doable
  output stays clean)'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/app/**
- docs/modules/tickets.md
- docs/modules/gates.md
- tests/test_gates_tick009_tick010.py
- tests/unit/test_app_runners_t0714_doable_summary.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'T-0714: TICK009/TICK010 doc anchor lives in gates.md; new dedicated test
    files for the relocated gate/summary'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_gates_tick009_tick010.py
  reason: 'T-0714: TICK009/TICK010 doc anchor lives in gates.md; new dedicated test
    files for the relocated gate/summary'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_app_runners_t0714_doable_summary.py
  reason: 'T-0714: TICK009/TICK010 doc anchor lives in gates.md; new dedicated test
    files for the relocated gate/summary'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_precisely_scoped_ticket_is_clean
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_chronically_over_broad_glob_warns
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_terminal_state_ticket_excluded
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_missing_worktree_reports_once_with_path_and_remedy
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_live_worktree_is_silent
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_five_stale_leases_each_reported_exactly_once
- tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_no_leases_directory_is_silent
- tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_no_nudges_prints_nothing
- tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line
designated_repro_test: null
acceptance:
- text: GIVEN 5 stale lease files WHEN frob ticket doable runs THEN the queue prints
    with at most one summary line about leases AND frob check (or doctor) reports
    each stale lease once with its path and remedy
  evidence:
  - tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport::test_five_stale_leases_each_reported_exactly_once
  - tests/unit/test_app_runners_t0714_doable_summary.py::TestRenderScopeBreadthSummary::test_multiple_stale_leases_collapse_to_one_summary_line
threat: null
component: null
---
User mandate 2026-07-22: frob ticket doable currently emits a wall of per-invocation diagnostics (stale-lease warnings -- 'T-XXXX lease references a worktree that no longer exists, treating as stale, skipped' -- repeated for every stale lease on EVERY queue query; observed 5 leases x repeated blocks flooding the session-start listing) plus scope/lease conflict notes. Doable's job is a clean ordered queue listing. Move the diagnostics: (1) doable emits the list only (a single summary line like 'N stale leases skipped, see frob check' is acceptable); (2) a check gate (LEASE001-style, warning tier) or the doctor reports stale leases, lease-worktree mismatches, and scope-conflict details ONCE with remediation (the lease file paths to clean); (3) log-level discipline per T-0202/T-0235 precedent -- the per-lease detail goes to DEBUG, not stdout.