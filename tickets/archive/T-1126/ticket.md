---
id: T-1126
title: 'daemon: wire run_coverage_wait through the daemon-owned coverage lease RPC
  (T-1097 follow-up)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_wait.py
- src/frob/app/_daemon_proxy.py
- tests/test_coverage_wait_shared.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
- tests/test_coverage_wait_shared.py::TestWorktreeLock::test_falls_back_to_file_lock_when_no_daemon
designated_repro_test: null
acceptance:
- text: GIVEN a running daemon WHEN run_coverage_wait needs the coverage writer THEN
    it acquires via the frob_lease_acquire RPC (crash-released per T-1097) instead
    of its own file-lock layers, with the file-lock path kept only as the daemonless
    fallback
  evidence:
  - tests/test_coverage_wait_shared.py::TestWorktreeLock::test_uses_daemon_lease_when_daemon_up
  - tests/test_coverage_wait_shared.py::TestWorktreeLock::test_falls_back_to_file_lock_when_no_daemon
threat: null
component: null
---
T-0321 epic close disclosed this cut: run_coverage_wait still uses its T-0322/T-1095 file-lock + shared-state layers directly; T-1097 shipped the daemon lease primitive (ResourceLeaseManager, frob_lease_acquire/release, connection-liveness release). Converge the two so coverage arbitration has ONE owner when a daemon is up.