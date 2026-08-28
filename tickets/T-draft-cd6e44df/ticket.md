---
id: T-draft-cd6e44df
title: Burn down remaining platform-unsafe test-fixture code surfaced by multi-platform
  ty (T-3211 split)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
- tests/test_ticket_land.py
- tests/unit/test_rapid_sweep.py
- tests/unit/test_process_lock.py
- tests/unit/test_coordinator_scripts.py
- tests/test_serve_socket.py
- tests/unit/test_stackdump.py
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_ticket_store.py
- tests/unit/test_app_runners_process.py
- tests/test_tickets_priority.py
- tests/test_tickets_parent.py
- tests/test_ticket_reconcile.py
- tests/test_coverage_wait_shared.py
- tests/test_app_daemon_proxy.py
- tests/unit/test_pytest_spawn_env_wiring.py
- tests/unit/test_land_lock_liveness.py
- tests/unit/test_land_finish_guard.py
- tests/test_serve_leases.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_new.py
- src/frob/verify/_worker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_leases.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_land.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_serve_socket.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_stackdump.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_app_runners_process.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_tickets_priority.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_tickets_parent.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_pytest_spawn_env_wiring.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_land_lock_liveness.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_land_finish_guard.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_serve_leases.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/_config_external.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/verify/_worker.py
  reason: exact 21-file list from the fresh T-3211-time ty measurement
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-3211, which fixed the 2 genuine product-code sites (scripts/fleet_status.py's os.major/os.minor/os.sysconf). The remaining ~197 ty findings (measured fresh via frob check --only ty on main at T-3211 time, 21 files: tests/test_ticket_leases.py, tests/test_ticket_land.py, tests/unit/test_rapid_sweep.py, tests/unit/test_process_lock.py, tests/unit/test_coordinator_scripts.py, tests/test_serve_socket.py, tests/unit/test_stackdump.py, tests/unit/test_conftest_stackdump.py, tests/unit/test_ticket_store.py, tests/unit/test_app_runners_process.py, tests/test_tickets_priority.py, tests/test_tickets_parent.py, tests/test_ticket_reconcile.py, tests/test_coverage_wait_shared.py, tests/test_app_daemon_proxy.py, tests/unit/test_pytest_spawn_env_wiring.py, tests/unit/test_land_lock_liveness.py, tests/unit/test_land_finish_guard.py, tests/test_serve_leases.py, src/frob/app/_config_external.py, src/frob/app/ticket_runner/_new.py, src/frob/verify/_worker.py) are unresolved-attribute/unknown-argument findings inside TEST bodies (mostly bare fcntl.flock/os.fork usage inside POSIX-only test fixtures, repeated many times across a small number of files -- tests/test_ticket_leases.py alone is 55 of the 197) plus 3 unused-ignore-comment findings on src files (a DIFFERENT bug shape -- a stale ty: ignore left over from before some earlier fix, not a missing platform guard; needs its own look, not the T-3191 pattern). WHAT TO BUILD: same triage T-3211 did -- re-measure fresh via frob check --only ty on current main (this list will have drifted further), then for each site either (a) apply the sys.platform-guard fix T-3191/T-3211 established, or (b) waive with a reason if it is a genuine false positive (e.g. a test class already coarsely POSIX-only). Given the volume, consider whether a shared pytest fixture/helper that wraps the fcntl.flock pattern once (rather than 8+ independent local imports in test_ticket_leases.py alone) is worth doing as part of this, to avoid 8 near-identical guards in one file.