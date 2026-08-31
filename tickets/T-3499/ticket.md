---
id: T-3499
title: 'macOS-only: 4 unrelated subprocess/env failures (bucket F, T-3488)'
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
- tests/test_tickets_evidence_cli.py;tests/test_app_daemon_proxy.py;tests/test_coverage.py;tests/test_coverage_sigterm.py
- tests/system/test_coverage_sigterm.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_coverage_sigterm.py
  reason: 'T-3499: original ticket named tests/test_coverage_sigterm.py, a path that
    does not exist -- the real file is tests/system/test_coverage_sigterm.py'
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'T-3499: BUG002 waiver -- macOS-only defect cannot fail-then-pass on this
    Linux worktree host'
  actor: logan
  at: '2026-08-30'
  old_length: 1827
  new_length: 2414
evidence:
- tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_repeated_sigterm_terminates_in_bounded_time
- tests/system/test_coverage_sigterm.py::TestCoverageSigtermDeadlock::test_normal_run_writes_complete_coverage_data
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while characterizing T-3488's macOS-only CI set (bucket F, 4 tests).

MEASURED (GitHub Actions run 33311990183, macos-latest): 4 unrelated
subprocess/env failures:

- tests/test_tickets_evidence_cli.py::test_shell_metacharacters_do_not_reach_a_shell
  (assert False) -- a shell-metacharacter-injection guard test; needs
  checking whether the guard's own subprocess call uses shell=True vs
  argv-list differently cross-platform, or whether the test's own
  injected-metacharacter fixture assumes a POSIX shell.
- tests/test_app_daemon_proxy.py::TestQuery::test_remote_error_falls_back
  (Unreachable is RemoteError) -- likely AF_UNIX socket path length
  limit: macOS's sockaddr_un path cap is 104 bytes vs Linux's 108, and
  tmp_path fixtures under macOS's longer /private/var/folders/... prefix
  can exceed it, turning a real connect attempt into ENOENT/Unreachable
  instead of the intended RemoteError fallback path.
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_produces_coverage_xml_after_worker_crash_recovery
  (1 == 2) -- worker-crash-recovery coverage count off by one; needs a
  macOS run to see which recovery path under/over-counts.
- tests/test_coverage_sigterm.py::test_repeated_sigterm_terminates_in_bounded_time
  (PermissionError: Operation not permitted) -- killpg targets a
  process group the macOS GHA runner sandbox does not let this process
  signal; likely needs to target the child's own pgid rather than a
  group that includes the runner's supervisory process.

Fix shape: four distinct root causes bundled here because each is small
and platform-specific; split into per-cause sub-tickets if a fix
attempt shows they are not actually independent. The AF_UNIX path-length
and killpg-pgid causes look most likely to be quick, real fixes rather
than boundaries to declare.

frob:waive BUG002 reason="T-3499 fixes one macOS-only sub-defect of bucket F (T-3488): killpg raising PermissionError on the macOS GHA runner's own sandbox even for a process's own group. The designated repro test genuinely PASSES at main on this Linux host (killpg never raises EPERM here), so it can only genuinely fail-then-pass on macos-latest CI, which this implementer cannot dispatch from a Linux worktree. Evidence is confirmatory-only on this host by the nature of the defect, not a weak test -- same shape as this drive's other BUG002 waivers (T-3488/T-3496/T-3498/T-3500)."