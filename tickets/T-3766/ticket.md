---
id: T-3766
title: skip win32-only AF_UNIX daemon-proxy tests
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_app_daemon_proxy.py
- tests/unit/test_daemon_proxy_error_paths_t1457.py
- tests/unit/test_daemon_proxy_lease_t1276.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: add BUG002 waiver
  actor: logan
  at: '2026-09-04'
  old_length: 29
  new_length: 16
- mode: set
  reason: restore body and add BUG002 waiver
  actor: logan
  at: '2026-09-04'
  old_length: 15
  new_length: 1045
evidence:
- tests/test_app_daemon_proxy.py::TestProbeDaemon::test_missing_socket_is_nosocket
- tests/test_app_daemon_proxy.py::TestQuery::test_no_daemon_no_socket_falls_back
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_connect_timeout_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_connect_oserror_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_hangup_before_newline_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_outer_timeout_during_send_or_recv_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths::test_call_oserror_closes_connection_and_returns_unreachable
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths::test_remote_error_response_closes_connection
- tests/unit/test_daemon_proxy_lease_t1276.py::TestDaemonLease::test_no_daemon_falls_back_unreachable
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Win32 CI failures: probe_daemon/query()/try_daemon_lease all short-circuit to ProxyReason.PlatformUnsupported / DaemonLiveness.PlatformUnsupported before touching socket.AF_UNIX on win32 (T-2961 guard). Affected tests assert POSIX-reachable values (NoSocket/Unreachable/Wedged) that the win32 early-return preempts. Add skipif(sys.platform == 'win32') to: TestProbeDaemon.test_missing_socket_is_nosocket, TestQuery.test_no_daemon_no_socket_falls_back (test_app_daemon_proxy.py); TestAskVersionOverSocket.{test_connect_oserror_is_wedged,test_connect_timeout_is_wedged,test_hangup_before_newline_is_wedged,test_outer_timeout_during_send_or_recv_is_wedged}, TestTryDaemonLeaseErrorPaths.{test_call_oserror_closes_connection_and_returns_unreachable,test_remote_error_response_closes_connection} (test_daemon_proxy_error_paths_t1457.py); TestDaemonLease.test_no_daemon_falls_back_unreachable (test_daemon_proxy_lease_t1276.py).

frob:waive BUG002 reason="win32-only skip; POSIX-primitive dependency not reproducible from a Linux parent-commit repro"