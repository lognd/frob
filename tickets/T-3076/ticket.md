---
id: T-3076
title: 'Characterize the 278 Windows-only test failures: 54 trace to five missing
  POSIX primitives, fcntl locking dominant'
state: queued
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
- docs/design/windows-portability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: Record the first real Windows suite measurement, the windows-only cluster
    breakdown, and its relationship to T-2916 and T-3003
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 4360
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33035660969, job 98397679871 (windows-latest),
the first run in which Windows got past Lint and Typecheck and actually
executed the suite:

    SUITE-RESULT: exitstatus=2 collected=12109 failed=365

Compare ubuntu-latest in the same run: 93 failed of 12,120. 88 of ubuntu's 93
ALSO fail on Windows, so the shared cross-platform defect set is 88 and the
WINDOWS-ONLY set is 278. This ticket owns the 278.

Note exitstatus=2 means INTERRUPTED, not a clean "tests failed" run. Some of
the 365 are plausibly cascade after the interrupt rather than independent
defects. Establish the real number by re-running to completion before treating
365 as a defect count -- do not build a burn-down against a number that has not
been shown to be stable.

WINDOWS-ONLY FAILURES BY ROOT CAUSE (clustered from the job log; the top
buckets are POSIX primitives that simply do not exist on Windows):

     22  ModuleNotFoundError: No module named 'fcntl'
     12  AttributeError: module 'os' has no attribute 'sysconf'
     10  AttributeError: module 'socket' has no attribute 'AF_UNIX'
      8  ValueError: cannot find context for 'fork'
      2  UnicodeEncodeError: 'charmap' codec can't encode character

That is 54 failures traceable to five named primitives. The remaining large
buckets are almost certainly downstream of the same five and should be
re-measured AFTER they are addressed rather than triaged independently:

     33  assert False
     16  assert None is not None
     11  SystemExit: 1
     11  AssertionError: assert False
     10  AssertionError: assert None is not None
      8  AssertionError: PerfError.SpawnFailed

Several failures are the platform-degradation path asserting the WRONG
direction -- e.g. `assert DaemonLiveness.PlatformUnsupported is
DaemonLiveness.<other>` and `assert ProxyReason.PlatformUnsupported is
ProxyReason.<other>`. Those are tests that already know about the boundary but
disagree with the code about which side of it Windows is on. They are cheap and
should be separated from the genuine missing-primitive work.

BY FILE, the windows-only concentration:
     41  tests/test_ticket_leases.py
     27  tests/test_gates.py
     20  tests/test_ticket_leases_cross_worktree.py
     17  tests/test_ticket_land.py
     14  tests/unit/test_coordinator_scripts.py
     14  tests/test_tickets_leases.py
     10  tests/test_app_daemon_proxy.py
      9  tests/test_hook_root_write_guard.py

The lease/land concentration is the important signal: `fcntl` is how file
locking is implemented, so leases, land serialization and the root-write guard
are all downstream of one missing module. Fix the locking primitive and a large
fraction of this list should move together.

RELATIONSHIP TO EXISTING TICKETS -- read before starting:
- T-2916 owns the DOCTRINE: frob is Linux-only in practice and degrades
  SILENTLY on Windows/macOS (locks no-op, orphan reaping disabled, CI cannot
  detect it). This ticket is the measured evidence for that claim, not a
  competing plan. Do not design a second portability story.
- T-3003 was filed when Windows failed roughly 19 tests, which was a
  measurement taken before Windows could run most of the suite. Its count is
  now known to be a floor, not the total. Reconcile it rather than duplicating.
- The PLATFORM001 doctrine applies throughout: declare the boundary loudly,
  never no-op silently. A lock that silently does nothing on Windows is worse
  than one that refuses.

ACCEPTANCE
- A completed (not interrupted) Windows run, with the stable failure count
  reported. If it still cannot complete, that is itself the finding and must be
  characterized.
- Each of the five named primitives has a declared cross-platform strategy: a
  real Windows implementation, or an explicitly declared and LOUD unsupported
  boundary. Silent no-op is not an acceptable outcome for any of them.
- File locking specifically must be correct on Windows or must refuse -- a
  silently no-op lease lock would let two agents write the same file, which is
  a correctness bug, not a portability nicety.
- The failures that are merely the degradation path asserting the wrong
  direction are separated out and fixed as their own small change.
- Post-fix re-measurement of the windows-only count, so the downstream buckets
  are re-triaged against reality rather than guessed at now.
