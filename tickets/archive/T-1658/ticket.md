---
id: T-1658
title: Audit and clear 19 WAIVE004 stale-waiver warnings post-T-1652 symref fix
state: done
kind: docs
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/_cli_parsers/_core.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/doctor.py
- src/frob/gates/__init__.py
- src/frob/release/__init__.py
- src/frob/serve/_events.py
- strata-core/src/parse/lexer.rs
- tests/system/test_cli_sys_audit.py
- tests/system/test_spawn_budget.py
- tests/test_dup_cross_lang.py
- tests/test_serve_daemon.py
- tests/test_ticket_leases.py
- tests/unit/perf/test_persist_run_cli.py
- tests/unit/perf/test_serial_pools.py
- tests/unit/perf/test_serial_pools_import_failure.py
- tests/unit/test_app_clean_runner_branches_t1400.py
- tests/unit/test_dup_cache.py
- tests/unit/test_land_release_coherence.py
- tests/unit/test_perf_runner_t1400.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: Every WAIVE004 finding classified (a/b/c); obsolete waivers removed; deletions
    declared in the Done report
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
T-1652 fixed dead_symbol_gate never setting Violation.symref, which had let
waiver matching silently fall back to file-scope for every DEAD001 waiver
(one waiver anywhere in a file was forgiving every DEAD001 finding in that
file). Fixing it made waiver matching bind exactly, and WAIVE004 (unscoped
count) rose from 10 to 19 as a direct, expected consequence: some fraction
of the 19 are newly-honest reports of waivers that were never really
covering what they claimed, not new debt.

This ticket audits all 19 current WAIVE004 warnings on a full unscoped
`frob check` run, classifies each (obsolete-remove / retarget-remove /
enroll-as-structurally-unverifiable), and removes/retargets waivers whose
underlying finding is confirmed gone.

Scope: only the frob:waive comment lines themselves (deletion), not the
functions/gates they sit beside. No gate logic changes expected -- this is
a hygiene pass over stale waiver directives across the tree.