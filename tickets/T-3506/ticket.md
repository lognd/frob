---
id: T-3506
title: 'Portable process lock: share the msvcrt/fcntl dual-path beyond derived_state_lock'
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: T-3505
tier: story
sprint: null
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_lock.py
- src/frob/process/_pid_liveness.py
- src/frob/serve/_leases.py
- src/frob/serve/_socketd.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land_queue.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_mutation_sweep_queue.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_store.py
- src/frob/verify/_watermark.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/gates/_narrative_blocks.py
- src/frob/gates/_walk_lint.py
- src/frob/testing/_coverage_wait.py
- tests/test_ticket_leases.py
- tests/test_ticket_leases_cross_worktree.py
- tests/test_ticket_land.py
- tests/test_hook_root_write_guard.py
- tests/test_tickets_leases.py
- tests/unit/test_coordinator_scripts.py
- tests/unit/test_ticket_store.py
- tests/unit/test_rapid_sweep.py
- tests/test_coverage_wait_shared.py
- tests/test_serve_socket.py
- docs/modules/process.md
- docs/modules/serve.md
- tests/unit/test_land_queue.py
- tests/unit/test_mutation_sweep_queue.py
- docs/design/registry/capability-via-ratchet.lock.json
- design/frob.strata
scope_breadth_ack: true
scope_breadth_ack_reason: one shared lock primitive genuinely fans out to every fcntl
  call site plus its lease/land/gate test files; T-3076's own by-file breakdown is
  the evidence for this exact file set
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/test_gates.py
  reason: T-3495 holds a live lease on this file; no new test needed here anyway --
    the 27 windows-only failures this ticket's brief cites in test_gates.py are gate
    tests exercising src/frob/gates/_narrative_blocks.py and _walk_lint.py (both in
    scope), which will pass once those modules stop importing fcntl directly, with
    no edit to the test file itself required
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: ledger_lock/_flock_path's own platform-backend tests monkeypatch fcntl/msvcrt
    as module-local attributes on frob.tickets._store, which now delegates to frob.process._lock's
    shared primitive -- must retarget the monkeypatch to keep exercising the real
    dual-path
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: ledger_lock/_flock_path's own platform-backend tests monkeypatch fcntl/msvcrt
    as module-local attributes on frob.tickets._store, which now delegates to frob.process._lock's
    shared primitive -- must retarget the monkeypatch to keep exercising the real
    dual-path
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: _baseline_lock's own platform-backend tests monkeypatch fcntl/msvcrt as
    module-local attributes on frob.app.ticket_runner._rapid_sweep, which now delegates
    to frob.process._lock's shared primitive -- must retarget the monkeypatch
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: _flock_path's own platform-backend tests monkeypatch fcntl/msvcrt as module-local
    attributes on frob.testing._coverage_wait, which now delegates to frob.process._lock's
    shared primitive -- must retarget the monkeypatch
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_serve_socket.py
  reason: acquire_singleton_lock's own platform-backend tests monkeypatch fcntl/msvcrt
    as module-local attributes on frob.serve._socketd, which now delegates to frob.process._lock's
    shared primitive -- must retarget the monkeypatch
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/process.md
  reason: 'AFFECT001 closure: derived_state_lock/portable_flock_acquire, acquire_singleton_lock,
    and file_lock/LandQueueLockUnavailable all changed and their frob:doc-anchored
    docs must reflect the T-3506 primitive extraction'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/serve.md
  reason: 'AFFECT001 closure: derived_state_lock/portable_flock_acquire, acquire_singleton_lock,
    and file_lock/LandQueueLockUnavailable all changed and their frob:doc-anchored
    docs must reflect the T-3506 primitive extraction'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'AFFECT001 closure: derived_state_lock/portable_flock_acquire, acquire_singleton_lock,
    and file_lock/LandQueueLockUnavailable all changed and their frob:doc-anchored
    docs must reflect the T-3506 primitive extraction'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'AFFECT001 closure: SweepQueueLockUnavailable and ledger_lock changed and
    their frob:doc-anchored docs must reflect the T-3506 primitive extraction'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'AFFECT001 closure: SweepQueueLockUnavailable and ledger_lock changed and
    their frob:doc-anchored docs must reflect the T-3506 primitive extraction'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001 closure: SweepQueueLockUnavailable and ledger_lock changed and
    their frob:doc-anchored docs must reflect the T-3506 primitive extraction'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_land_queue.py
  reason: adding LandQueueLockUnavailable/SweepQueueLockUnavailable no-backend-refuses-loudly
    tests, required by frob ticket land's T-2114 new-public-symbol coverage gate
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_mutation_sweep_queue.py
  reason: adding LandQueueLockUnavailable/SweepQueueLockUnavailable no-backend-refuses-loudly
    tests, required by frob ticket land's T-2114 new-public-symbol coverage gate
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001 ratchet-ceiling bump for the new testsuite fs.read site
  actor: logan
  at: '2026-08-30'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001: removed stale may eval declarations for serve/tickets_ledger
    nodes -- their importlib.import_module fcntl/msvcrt calls were centralized into
    frob.process._lock'
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: docs/modules/tickets-data-storage.md
  reason: reverted content edits to these 4 files -- all under T-3520's own open scope,
    causing CrossTicketLeakage on land; resolved the AFFECT001 findings via frob:waive
    at each symbol instead of a doc prose touch
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: docs/modules/tickets-landing.md
  reason: reverted content edits to these 4 files -- all under T-3520's own open scope,
    causing CrossTicketLeakage on land; resolved the AFFECT001 findings via frob:waive
    at each symbol instead of a doc prose touch
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: reverted content edits to these 4 files -- all under T-3520's own open scope,
    causing CrossTicketLeakage on land; resolved the AFFECT001 findings via frob:waive
    at each symbol instead of a doc prose touch
  actor: logan
  at: '2026-08-30'
- op: remove
  glob: docs/modules/tickets.md
  reason: reverted content edits to these 4 files -- all under T-3520's own open scope,
    causing CrossTicketLeakage on land; resolved the AFFECT001 findings via frob:waive
    at each symbol instead of a doc prose touch
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_process_lock.py::TestPortableFlock::test_posix_blocking_acquire_release_round_trips
- tests/unit/test_process_lock.py::TestPortableFlock::test_posix_nonblocking_contended_returns_false
- tests/unit/test_process_lock.py::TestPortableFlock::test_windows_branch_selected_when_fcntl_absent
- tests/unit/test_process_lock.py::TestNoDirectFcntlOutsideSharedPrimitive::test_no_direct_fcntl_import_outside_lock_module
- tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends::test_windows_backend_round_trips
- tests/unit/test_ticket_store.py::TestLedgerLockPlatformBackends::test_windows_backend_round_trips
- tests/unit/test_process_lock.py::TestSharedIdCounterPlatformBackends::test_windows_backend_round_trips
- tests/ticket_land_suite/test_land_lock.py::TestLandLockPlatformBackends::test_windows_backend_round_trips
- tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_windows_backend_round_trips
- tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_windows_backend_round_trips
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_windows_backend_serializes_two_concurrent_holders
- tests/unit/test_land_queue.py::TestFileLock::test_no_lock_primitive_refuses_loudly
- tests/unit/test_mutation_sweep_queue.py::TestSweepLockPlatformBackend::test_no_lock_primitive_refuses_loudly
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0cebc2819d90ec650e424422313ab2c3cc41e3cf
---
Adopt a single portable process-lock primitive for the OTHER fcntl call
sites, mirroring the dual-path (fcntl/msvcrt) approach
src/frob/process/_lock.py::derived_state_lock already uses.

MEASURED: 22 of T-3076's 278 windows-only failures are
ModuleNotFoundError: No module named 'fcntl'. This is the single
largest primitive bucket and the one T-3076 flags as most consequential
-- fcntl backs file locking used by leases, land serialization and the
root-write guard, so BY FILE the windows-only concentration (from
T-3076) is dominated by this cluster:
  41  tests/test_ticket_leases.py
  27  tests/test_gates.py
  20  tests/test_ticket_leases_cross_worktree.py
  17  tests/test_ticket_land.py
   9  tests/test_hook_root_write_guard.py
   (plus test_tickets_leases.py, test_coordinator_scripts.py)

DESIGN: src/frob/process/_lock.py already imports fcntl defensively
(fcntl = None if unavailable) and dual-paths derived_state_lock between
fcntl.flock (POSIX) and msvcrt (Windows). Extract that dual-path lock
into a shared, reusable primitive in src/frob/process/ (e.g. a
`portable_flock(fd, exclusive) -> None` / context manager) and have
every OTHER direct `import fcntl` / `fcntl.flock(...)` call site adopt
it instead of importing fcntl directly. Do NOT re-derive a second
msvcrt branch per call site -- one home, per the no-duplication
principle.

FILES IN SCOPE (measured via `git grep -ln fcntl -- src`):
  src/frob/process/_lock.py            (already dual-paths; source of
                                         the primitive to extract/share)
  src/frob/process/_pid_liveness.py
  src/frob/serve/_leases.py
  src/frob/serve/_socketd.py
  src/frob/tickets/_land.py
  src/frob/tickets/_land_git_ops.py
  src/frob/tickets/_land_queue.py
  src/frob/tickets/_leases.py
  src/frob/tickets/_mutation_sweep_queue.py
  src/frob/tickets/_new_renumber.py
  src/frob/tickets/_store.py
  src/frob/verify/_watermark.py
  src/frob/app/ticket_runner/_rapid_sweep.py
  src/frob/gates/_narrative_blocks.py
  src/frob/gates/_walk_lint.py
  src/frob/testing/_coverage_wait.py

MUST-FIRE (acceptance)
- No module under src/frob imports fcntl directly except the shared
  primitive's own home (src/frob/process/_lock.py or its extracted
  successor module).
- On Windows, file locking is REAL (msvcrt-backed, correct mutual
  exclusion) or LOUDLY refuses -- per PLATFORM001 doctrine, never a
  silent no-op. A silently no-op lease lock is a correctness bug (two
  agents could write the same file), not acceptable degradation.
- The 41+27+20+17+9 windows-only failures in the files listed above
  collapse to (near-)zero once this lands; re-measurement happens in
  the re-measure leaf, not here.

MUST-STAY-QUIET (acceptance)
- POSIX behavior (existing fcntl.flock semantics, timeouts, LOCK_EX/
  LOCK_SH) is byte-for-byte unchanged on Linux/macOS -- this is a
  Windows-additive change, not a POSIX refactor.
- Existing POSIX lease/land/gate/coordinator test suites stay green
  with no new skips.

SCOPE GROUPING: this leaf is scope-disjoint from the os.sysconf,
AF_UNIX, fork-context and charmap leaves below (different files, no
overlap) -- dispatchable in parallel with all four.
