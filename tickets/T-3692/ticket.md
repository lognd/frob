---
id: T-3692
title: 'win32 round 22: post-submit 122s + watchdog var bug + mac flake'
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/process/**
- tests/conftest.py
- .github/workflows/ci.yml
- tests/unit/test_check_admission.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: waive BUG002/DIAG
  actor: logan
  at: '2026-09-02'
  old_length: 2768
  new_length: 3185
evidence:
- tests/unit/test_check_admission.py::TestTimingDebug::test_disabled_by_default
- tests/unit/test_check_admission.py::TestTimingDebug::test_mark_prints_breadcrumb_when_enabled
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3689/T-3686. CI run 33625622797's FROB-CHECK-TIMING
breadcrumbs localized the win32 122s decisively: entry->submit completes
in ~1s (max 0.954s) in every variant; the delay is entirely POST-submit
(gate execution / collect / report / teardown), and it is FROB_DISABLE_EXEC
-specific (zero-tool-spawn variant: 123.1s; baseline: 9.5s; direct-python:
3.8s; pool-preload: 3.9s).

PART A: extend timing instrumentation past 'submit' -- mark after gate
execution/collect (already have 'collected' from T-3689), after report
construction, and through teardown (console-ctrl scope __exit__,
admission-registry __exit__/cleanup, an atexit breadcrumb to catch
interpreter-shutdown-phase delay e.g. a non-daemon thread join). Grep the
check/admission/process teardown paths for a ~120s timeout/join
(_MSVCRT_BLOCKING_ACQUIRE_CEILING_S = 120.0 in frob.process._lock is the
prime numeric match to the observed 123.1s, though its own derived_state_
lock call sites do not appear to be reachable from a ThreadPoolExecutor
worker while the main thread holds the run-wide SHARED lock, per static
read -- the new breadcrumbs should confirm or rule this out on the next
windows run). Also plausible and OUT OF THIS TICKET'S SCOPE to fix
directly: frob.gates._open_process_pool's ProcessPoolExecutor (forkserver
falls back to spawn on win32, which cold-imports frob.gates per worker) --
noted for a follow-up ticket if confirmed.

PART B: ci.yml's Windows Test step prints "Windows Test step exceeded
$budget s" with $budget literally unexpanded in run 33625622797's log,
AND the 180s (T-3689) midrun watchdog never fired -- investigate the
var-expansion/env-propagation shape and fix so FROB_TEST_MIDRUN_WATCHDOG_
SECONDS reliably trips at 180s with a real diagnostic, never a silent
1500s timeout.

PART C: tests/unit/test_check_admission.py::TestTimingDebug::
test_mark_prints_breadcrumb_when_enabled failed on macOS in run
33625622797 -- its `elapsed < 60.0` bound assumes _timing_mark is called
shortly after `_TIMING_PROCESS_START` (captured at frob.check's MODULE
IMPORT time), but in a live pytest process that import happens once at
collection and this test can run minutes later, especially on a slower/
loaded macOS runner -- not flaky, GUARANTEED to fail eventually. Fix by
monkeypatching _TIMING_PROCESS_START to a known-recent value, matching
the sibling test test_mark_elapsed_grows_with_process_start_offset's own
pattern. Also check tests/unit/test_daemon_proxy_lease_t1276.py::
TestDaemonLease::test_round_trip_acquire_call_release_close (also failed
on mac this run) -- determine if it is fallout from T-3689's diff or an
unrelated flake; fix only if ours (that file is likely out of this
ticket's own scope).

References: T-3689, T-3686, T-3683, T-3256.



frob:waive BUG002 reason="win32-only symptom (122s post-submit teardown slowdown) unreproducible on this WSL/Linux host by construction -- this land ships diagnostic timing marks (report/teardown/atexit) plus a hypothesis-fix (ci.yml env/var-expansion hardening) for the NEXT windows CI run to confirm or refute, matching T-3689/T-3693 round precedent; no local repro test can exercise a win32-specific code path"