---
id: T-3518
title: 'macOS-only: 3 unmeasured bucket-F failures (T-3499 follow-up)'
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets_evidence_cli.py
- tests/test_app_daemon_proxy.py
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: all 3 fixed defects are macOS-only, unreproducible on Linux
    CI'
  actor: logan
  at: '2026-08-30'
  old_length: 2240
  new_length: 3105
evidence:
- tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
- tests/test_app_daemon_proxy.py::TestQuery::test_remote_error_falls_back
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-3499 (which itself followed from T-3488 bucket F): 3
of the 4 bundled bucket-F failures were NOT fixable from a Linux
worktree without further macOS measurement (T-3499 fixed the 4th,
killpg PermissionError, landed at c8013b0b3c4cc3f48871ed0dec3b3184d5da36ad).

1. tests/test_tickets_evidence_cli.py::test_shell_metacharacters_do_not_reach_a_shell
   (assert False). _run_evidence_command uses shlex.split + argv exec
   via guarded_subprocess_run -- pure-Python stdlib logic, platform-
   identical for a given Python version. No platform-dependent code
   path was found to explain a different outcome on macOS without
   reproducing the actual printf/shlex behavior there. Needs: run the
   crafted command ("printf hi; touch <marker>") on a macOS box (or the
   -vv CI log) to see whether printf itself exits nonzero there (BSD
   printf's handling of surplus positional arguments after a format
   string with no conversion specifiers may differ from GNU printf's).

2. tests/test_app_daemon_proxy.py::TestQuery::test_remote_error_falls_back
   (Unreachable is RemoteError). T-2945 already fixed the general
   AF_UNIX sun_path-length hazard (socket moved to
   <tempdir>/frob-<16hex>.sock, independent of project depth). The
   observed "Unreachable is RemoteError" shape means send_request never
   actually reached the daemon at all on macOS -- a residual AF_UNIX
   path-length case in this test's own tmp_path-based root, a daemon
   spawn race on macOS's own process/thread scheduling, or something
   else entirely. Needs a live macOS repro (or -vv CI log with the
   actual OSError/connect failure) to isolate which.

3. tests/test_coverage.py::TestNativeCoverageRefresh::
   test_full_run_produces_coverage_xml_after_worker_crash_recovery
   (1 == 2). A worker-crash-recovery coverage COUNT off-by-one. Needs a
   macOS-side trace of which recovery path under/over-counts -- not
   evident from the Linux-side recovery logic alone; likely needs
   -vv/print-instrumented output from an actual macOS CI run.

ACCEPTANCE: each of the 3 above measured (via a macOS box or a -vv CI
log for that node id) and either fixed (hermetic, no unconditional
skip) or a PLATFORM001 declared boundary with the reason stated.

<!-- frob:waive BUG002 reason="all 3 defects this ticket fixes are macOS-only: (1) the printf argv-shape difference is BSD-printf-vs-GNU-printf, both this ticket's designated repro test and the other 2 evidence tests pass identically at the parent commit and at the fix on this repo's own Linux CI runner, because GNU printf and Linux thread-scheduling/memory-measurement never hit the failure mode being fixed; (2) the daemon-readiness race is specific to macOS's slower thread scheduling relative to query()'s 1.5s _SPAWN_GRACE_S window; (3) the worker-count/-n-flag test depends on _available_memory_mb's real /proc/meminfo read, which only degrades to None on non-Linux. None of these can be reproduced by a test running on this platform -- only observed on macos-latest CI (T-3076-family macOS bucket F, T-3499 follow-up, runs 33342928809/33340976639)." -->