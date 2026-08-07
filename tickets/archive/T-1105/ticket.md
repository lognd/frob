---
id: T-1105
title: 'daemon: real version-handshake RPC on the socket daemon (replace sidecar meta-file
  skew detection)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: T-0321
tier: ticket
sprint: null
scope:
- src/frob/serve/_socketd.py
- src/frob/app/_daemon_proxy.py
- tests/test_app_daemon_proxy.py
- docs/modules/serve.md
- tests/test_serve_socket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_serve_socket.py
  reason: frob_version/frob_shutdown RPC additions to _socketd.py need direct socket-level
    test coverage in this file, not just via the proxy's own test file
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_serve_socket.py::TestDispatchRequest::test_frob_version_reports_daemon_version
- tests/test_serve_socket.py::TestDispatchRequest::test_frob_shutdown_stops_the_server
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_spawns_when_nothing_recorded
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_noop_when_version_matches
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_version_handshake_end_to_end
- tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew
designated_repro_test: null
acceptance:
- text: given a running daemon of a different frob version, when the proxy queries
    it, then skew is detected via a daemon-side version RPC (not the .frob/daemon.meta.json
    sidecar), the stale daemon is replaced, and the query succeeds
  evidence:
  - tests/test_app_daemon_proxy.py::TestEnsureDaemon::test_restarts_on_version_skew
threat: null
component: null
---
Refile of T-1093's dead draft T-1105 (lost in the 10b worktree-ledger restore before land). T-1093 shipped sidecar-file skew detection because src/frob/serve/** was a sibling's scope that wave; this moves the version handshake into the daemon protocol proper.