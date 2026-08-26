---
id: T-2944
title: PLATFORM001 misses sys.platform-string guards; /proc-only worktree-liveness
  scan is permissive on macOS/Windows
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_walk_lint.py
- src/frob/process/_reap.py
- src/frob/tickets/_leases.py
- tests/unit/test_process_reap.py
- tests/unit/test_land_finish_guard.py
- docs/modules/process.md
- docs/modules/gates.md
evidence_scope:
- tests/test_walk_lint_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/process.md
  reason: 'AFFECT001 requires docs/modules/process.md''s forkserver-reaping-t-2443
    section to move alongside arm_parent_death_signal''s body change (a WARNING log
    added to the sys.platform guard, T-2944''s Part 1 fix); needed to satisfy the
    affects()-closure gate.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001 requires docs/modules/gates.md''s PLATFORM001 section to move
    alongside walk_lint_gate''s body change (the two new PLATFORM001 detection shapes,
    T-2944 Part 1); needed to satisfy the affects()-closure gate.

    '
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_walk_lint_gate.py::TestPlatform001StringGuard::test_silent_string_guard_fires
- tests/test_walk_lint_gate.py::TestPlatform001StringGuard::test_logged_string_guard_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001StringGuard::test_real_platform_branch_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001StringGuard::test_boolop_guard_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001StringGuard::test_gate_fires_end_to_end
- tests/test_walk_lint_gate.py::TestPlatform001BareImport::test_bare_import_fires
- tests/test_walk_lint_gate.py::TestPlatform001BareImport::test_guarded_import_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001BareImport::test_gate_fires_end_to_end
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured while triaging T-2930's macOS CI run (T-2917 PR#1, run
32920399634, job 98032723003).

PART 1 -- gate coverage gap (report, not yet fixed): PLATFORM001
(T-2919) only detects the shape `try: import X / except ImportError:
X = None / if X is None: <log, no raise>` -- an IMPORT-AVAILABILITY
guard. `src/frob/process/_reap.py::arm_parent_death_signal` degrades
on non-Linux via a DIFFERENT shape entirely:

    if sys.platform != "linux":
        return False

a platform-STRING guard with no log call in that branch at all (the
caller, `_arm_forkserver_helper_pdeathsig_if_requested`, does log a
WARNING on a `False` return, so this specific site is not silently
degrading in practice -- but the gate itself has zero visibility into
it). Verified directly: `frob check --only walk_lint --json` on this
repo's own HEAD fires PLATFORM001 15 times, none of them
`_reap.py:192`. This means ANY future `sys.platform != "..."` guard
added anywhere in `src/frob/**` that silently swallows a platform gap
(no accompanying manual log/raise the way this one happens to have)
would ship completely undetected by the gate whose entire job is
catching exactly that. `_walk_lint.py::_platform_guard_names` needs a
second detection shape alongside the existing `X is None` one: an
`if sys.platform (!=|==) "<literal>":` test whose body neither raises/
exits (`_guard_is_loud`) nor logs (`_guard_logs`).

PART 2 -- real degrade, needs a design decision (per T-2930's own
brief: NOT to be silently worked around): `arm_parent_death_signal`
itself only implements PDEATHSIG via Linux's `prctl(PR_SET_PDEATHSIG)`;
there is no macOS fallback. macOS DOES have a real equivalent
mechanism -- kqueue's `EVFILT_PROC`/`NOTE_EXIT` filter registered on
the parent's pid, which delivers an event when the parent process
exits, close enough to PDEATHSIG's semantics to replace it (watch for
the event in a small thread/loop and self-signal on delivery, same as
the Linux path's post-arm self-check already does for its own race
window). Implementing this is real, scoped work (a new `_reap_kqueue.
py`-shaped module, or a platform branch inside `arm_parent_death_
signal` itself) -- deliberately not attempted here per T-2930's brief
(the design choice of whether to invest in it belongs to whoever owns
process.md's roadmap, not a triage ticket). If declined, the
alternative the brief calls for is escalating `_reap.py`'s existing
WARNING-level call-site log to something a macOS operator cannot miss
(it is already loud today, just worth an explicit ack that "loud, not
silent" is the deliberately chosen non-Linux posture here, not an
oversight).

PART 3 -- same class of gap, more actively dangerous direction:
`src/frob/tickets/_leases.py::scan_for_live_worktree_process` is
`/proc`-only (`Path("/proc")` walk) and returns `None` -- "no live
process found" -- on any platform without `/proc`, i.e. macOS and
Windows both. Unlike Part 2 (which degrades toward the SAFE direction,
just not arming a kill-on-parent-death guard), this degrades toward
the PERMISSIVE direction: `frob ticket land --finish` (T-1715) and
`frob worktree sweep` (T-1739) both call this as their belt-and-braces
check before removing a worktree a live process might still be cwd'd
into, and on macOS/Windows it ALWAYS reports "no live process" even
when one genuinely is, silently disabling the safety check itself.
This is the higher-priority of the two process-detection gaps in this
ticket. 4 of the 156 measured macOS failures are in this cluster
(tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess
and TestFinishWorktree's guard-refusal tests) -- the tests are
CORRECTLY failing (they expect a real find that `/proc`-only code
cannot produce off Linux), so this is a genuine product gap, not
test-only fragility. A macOS-native alternative exists
(`sysctl(KERN_PROC, KERN_PROC_ALL)` enumeration via ctypes, or
shelling out to `lsof +D <path>` / `fuser <path>` if present) and is
real, scoped work for its own ticket -- not attempted here.