---
id: T-3211
title: Burn down platform-unsafe code surfaced by multi-platform ty (T-3191)
state: done
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
- scripts/fleet_status.py
- tests/system/test_fleet_status_ground_truth.py
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: N/A
  reason: narrowed to the two genuine platform-unsafe product-code findings (os.major/os.minor/os.sysconf)
    this triage pass fixes; remaining test-fixture files split to a follow-up ticket
  actor: logan
  at: '2026-08-28'
- op: add
  glob: scripts/fleet_status.py
  reason: narrowed to the two genuine platform-unsafe product-code findings (os.major/os.minor/os.sysconf)
    this triage pass fixes; remaining test-fixture files split to a follow-up ticket
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/system/test_fleet_status_ground_truth.py
  reason: narrowed to the two genuine platform-unsafe product-code findings (os.major/os.minor/os.sysconf)
    this triage pass fixes; remaining test-fixture files split to a follow-up ticket
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: must-fire/must-stay-quiet fixtures for the new _flock_holders_matching win32
    guard
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_coordinator_scripts.py::TestFlockHoldersMatchingWin32Guard::test_win32_platform_returns_empty_without_calling_os_major_minor
- tests/unit/test_coordinator_scripts.py::TestFlockHoldersMatchingWin32Guard::test_posix_platform_still_matches_normally
- tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_fire_the_true_holder_among_waiters
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestFlockHoldersMatchingWin32Guard::test_win32_platform_returns_empty_without_calling_os_major_minor
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3191 wired frob.check._python._run_ty to run ty check once per
platform in frob.toml's [ty] target_platforms (default
linux/win32/darwin) instead of only the host platform. This is
STRUCTURALLY CORRECT and intentional (PLATFORM001 doctrine: declare the
boundary, don't hide it) -- but it immediately surfaces a large batch of
PRE-EXISTING platform-unsafe code across the repo that a host-only ty
check never saw before, measured via frob check --ticket T-3191's
error-findings list right after T-3191 landed:

unresolved-attribute / unknown-argument findings (real ty diagnostics,
not frob's own gate codes) in at least: scripts/fleet_status.py,
tests/test_app_daemon_proxy.py, tests/test_coverage_wait_shared.py,
tests/test_serve_leases.py, tests/test_serve_socket.py,
tests/test_ticket_land.py, tests/test_ticket_leases.py,
tests/test_ticket_reconcile.py, tests/test_tickets_parent.py,
tests/test_tickets_priority.py, tests/unit/test_conftest_stackdump.py,
tests/unit/test_coordinator_scripts.py,
tests/unit/test_land_finish_guard.py,
tests/unit/test_land_lock_liveness.py, tests/unit/test_process_lock.py,
tests/unit/test_rapid_sweep.py, tests/unit/test_stackdump.py,
tests/unit/test_ticket_store.py.

These are exactly the same bug SHAPE T-3191 fixed for
frob.process._reap/_pid_liveness: POSIX-only stdlib/ctypes access
(fcntl, os.fork, resource.*, etc.) not behind a sys.platform ==
guard ty can narrow per --python-platform target, so it was invisible
under a host-only Linux check and only shows up once win32/darwin
targets are checked too.

Not fixed here -- T-3191's own scope was exactly two named files. This
is the out-of-scope discovery filed per that ticket's own "found work
outside scope, file a ticket" instruction. Per the repo's existing
--ticket attribution-first gating, this does NOT block any other
ticket's close (repo-wide gate counts are not scoped to a ticket unless
the finding is in that ticket's own diff), so it is safe to leave queued
rather than treated as urgent.

WHAT TO BUILD: triage the full list (re-measure fresh via
frob check --only ty on current main, since this list will drift as
other tickets land), then for each site either (a) apply the same
sys.platform-guard fix T-3191 used for _reap.py/_pid_liveness.py, or (b)
determine it's a false positive (e.g. a test fixture that legitimately
only runs on POSIX and is itself platform-guarded at a coarser level,
e.g. pytest.mark.skipif) and waive with a reason, never silently.