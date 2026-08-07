---
id: T-1457
title: 'app TEST005 genuine gaps: telemetry and _daemon_proxy socket/subprocess error
  paths'
state: done
kind: feature
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/telemetry.py
- src/frob/app/_daemon_proxy.py
- tests/unit/**
- tests/test_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_telemetry.py
  reason: 'T-1457''s declared scope covers src/frob/app/telemetry.py plus tests/unit/**,

    but the existing test suite for telemetry.py lives at tests/test_telemetry.py

    (not under tests/unit/). New OSError-swallow/git-unavailable-fallback error-

    path tests were added there, alongside the existing suite, rather than

    forking a second test module under tests/unit/ for the same source file --

    adding this one file keeps the frob:tests edge resolvable inside scope.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_telemetry.py::test_append_event_swallows_oserror_and_logs
- tests/test_telemetry.py::test_tree_hash_returns_unknown_when_git_spawn_errors
- tests/test_telemetry.py::test_tree_hash_returns_unknown_on_nonzero_returncode
- tests/test_telemetry.py::test_tree_hash_returns_stripped_stdout_on_success
- tests/test_telemetry.py::test_record_ticket_event_merges_extra_fields
- tests/test_telemetry.py::test_timed_call_records_nonzero_exit_on_plain_exception
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_connect_timeout_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_connect_oserror_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_hangup_before_newline_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_outer_timeout_during_send_or_recv_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_malformed_json_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_non_dict_result_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_non_str_version_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_bad_utf8_is_wedged
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClearOrphanedSocket::test_unlink_oserror_is_swallowed
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClientVersion::test_unexpected_exception_falls_back_to_unknown
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestSpawnDaemon::test_popen_oserror_is_swallowed
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon::test_rpc_failure_is_logged_and_returns
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon::test_successful_shutdown_waits_for_lock_release
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths::test_call_oserror_closes_connection_and_returns_unreachable
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths::test_remote_error_response_closes_connection
- tests/unit/test_daemon_proxy_error_paths_t1457.py::TestReleaseDaemonLease::test_call_oserror_is_swallowed_and_connection_still_closed
designated_repro_test: null
acceptance:
- text: GIVEN the named error-path branches WHEN their tests run THEN each asserts
    real behavior (fallback value, exit code, log line), never mere execution
  evidence:
  - tests/test_telemetry.py::test_append_event_swallows_oserror_and_logs
  - tests/test_telemetry.py::test_tree_hash_returns_unknown_when_git_spawn_errors
  - tests/test_telemetry.py::test_tree_hash_returns_unknown_on_nonzero_returncode
  - tests/test_telemetry.py::test_tree_hash_returns_stripped_stdout_on_success
  - tests/test_telemetry.py::test_record_ticket_event_merges_extra_fields
  - tests/test_telemetry.py::test_timed_call_records_nonzero_exit_on_plain_exception
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_connect_timeout_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_connect_oserror_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_hangup_before_newline_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestAskVersionOverSocket::test_outer_timeout_during_send_or_recv_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_malformed_json_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_non_dict_result_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_non_str_version_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClassifyVersionReply::test_bad_utf8_is_wedged
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClearOrphanedSocket::test_unlink_oserror_is_swallowed
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestClientVersion::test_unexpected_exception_falls_back_to_unknown
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestSpawnDaemon::test_popen_oserror_is_swallowed
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon::test_rpc_failure_is_logged_and_returns
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestShutdownStaleDaemon::test_successful_shutdown_waits_for_lock_release
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths::test_call_oserror_closes_connection_and_returns_unreachable
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestTryDaemonLeaseErrorPaths::test_remote_error_response_closes_connection
  - tests/unit/test_daemon_proxy_error_paths_t1457.py::TestReleaseDaemonLease::test_call_oserror_is_swallowed_and_connection_still_closed
threat: null
component: null
---
Wave5-O's classification (T-1400 Done report) isolated the app package's only real TEST005 gaps: telemetry.py (OSError-swallow, git-unavailable fallback, non-int SystemExit-code branches) and _daemon_proxy.py (~80 percent both narrow and wide: _probe_daemon, _classify_version_reply, _spawn_daemon, _shutdown_stale_daemon socket/subprocess error paths). Both need socket/subprocess seam mocking (T-1276's daemon-lease test precedent). Everything else sampled in app/strata was attribution artifact -- see T-1400/T-1415 Done reports for the tally.